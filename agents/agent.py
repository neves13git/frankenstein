# agent.py - LangGraph/LLM Agent para diagnóstico e correção

import requests
import os
import time
from requests.exceptions import HTTPError 


# URLs separadas para cada serviço
SYSTEM_SIMULATOR_URL = "http://localhost:9000"
MCP_SERVER_URL = "http://localhost:9100"
CLIENT_ID = "1"


# Mock base de procedimentos (simula RAG)
docs = [
    {"symptom": "erro de conexão", "procedure": "Ativar sistema", "action": "update_system_by_id", "params": {"is_active": True}},
    {"symptom": "sistema inativo", "procedure": "Ativar sistema", "action": "update_system_by_id", "params": {"is_active": True}},
]


def mcp_get_tools():
    """Busca a lista de ferramentas e seus schemas do MCP Server."""
    try:
        r = requests.get(f"{MCP_SERVER_URL}/tools")
        r.raise_for_status()
        tools = r.json()["tools"]
        # Busca detalhes de cada tool
        schemas = {}
        for tool_name in tools:
            # Supondo endpoint /tool_schema/{tool_name} retorna o schema da tool
            try:
                resp = requests.get(f"{MCP_SERVER_URL}/tool_schema/{tool_name}")
                resp.raise_for_status()
                schemas[tool_name] = resp.json()
            except Exception:
                schemas[tool_name] = None
        return schemas
    except Exception as e:
        print(f"[Agent] ERRO ao obter schemas das ferramentas: {e}")
        return {}


def mcp_get_systems(client_id):
    """
    Busca o status dos sistemas do cliente (System Simulator).
    """
    # Usar SYSTEM_SIMULATOR_URL para montar a URL base.
    url = f"{SYSTEM_SIMULATOR_URL}/api/v1/system1/{client_id}"
    try:
        print(f"[Agent] GET sistemas: {url}")
        r = requests.get(url)
        r.raise_for_status()
        print(f"[Agent] Resposta sistemas: {r.text}")
        # Assume-se que o endpoint retorna uma LISTA de sistemas diretamente.
        return r.json()
    except HTTPError as e:
        print(f"[Agent] ERRO HTTP ao obter sistemas ({e.response.status_code}): {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Agent] ERRO de Conexão ao obter sistemas: {e}")
        return []


def mcp_execute_action(client_id, action, params):
    """
    Executa uma ação no MCP Server (Tool Executor).
    """
    print(f"[Agent] Solicitando ao MCP Server execução da ação: {action} com params: {params}")
    try:
        r = requests.post(f"{MCP_SERVER_URL}/call_tool", json={
            "name": action,
            "arguments": params
        })
        r.raise_for_status()
        print(f"[Agent] Resposta MCP Server: {r.text}")
        return r.json()
    except HTTPError as e:
        print(f"[Agent] ERRO HTTP ao executar ação ({e.response.status_code}): {e}")
        return {"status": "error", "message": f"Falha na execução: {e.response.text}"}
    except requests.exceptions.RequestException as e:
        print(f"[Agent] ERRO de Conexão ao executar ação: {e}")
        return {"status": "error", "message": f"Falha de conexão: {e}"}


def agent_run(json_input):
    client_id = json_input["client_id"]
    run_log = []
    max_cycles = 3

    cycle = 0
    while cycle < max_cycles:
        print(f"[Agent] Diagnóstico ciclo {cycle+1}")
        systems = mcp_get_systems(client_id)
        run_log.append({"step": "get_systems", "output": systems})

        if not systems and cycle == 0:
            print("[Agent] Não foi possível obter o estado inicial dos sistemas.")
            return {"result": "service_unavailable", "log": run_log}

        problemas = [s for s in systems if not s.get("is_active", True) or s.get("error_message")]
        if not problemas:
            print("[Agent] Nenhum problema encontrado.")
            return {"result": "resolved", "log": run_log}


        # Só trata UM problema por ciclo

        run_log = []
        max_cycles = 3
        # Busca schemas das tools
        tool_schemas = mcp_get_tools()

        cycle = 0
        while cycle < max_cycles:
            print(f"[Agent] Diagnóstico ciclo {cycle+1}")
            systems = mcp_get_systems(client_id)
            print(f"[Agent] Sistemas recebidos: {systems}")
            run_log.append({"step": "get_systems", "output": systems})

            if not systems and cycle == 0:
                print("[Agent] Não foi possível obter o estado inicial dos sistemas.")
                return {"result": "service_unavailable", "log": run_log}

            problemas = [s for s in systems if not s.get("is_active", True) or s.get("error_message")]
            print(f"[Agent] Problemas detectados: {problemas}")
            if not problemas:
                print("[Agent] Nenhum problema encontrado.")
                return {"result": "resolved", "log": run_log}

            problema = problemas[0]
            print(f"[Agent] Problema selecionado: {problema}")
            symptom_text = problema.get("error_message") or "sistema inativo"
            hit = next((d for d in docs if d["symptom"] in symptom_text), None)
            print(f"[Agent] Procedimento encontrado: {hit}")
            run_log.append({"step": "rag_search", "symptom": symptom_text, "hit": hit})

            if not hit:
                print(f"[Agent] Nenhum procedimento encontrado para sintoma: {symptom_text}")
                break

            tool_schema = tool_schemas.get(hit["action"])
            print(f"[Agent] Tool schema: {tool_schema}")
            params = {}
            if tool_schema and "inputSchema" in tool_schema:
                input_schema = tool_schema["inputSchema"]
                for field in input_schema.get("properties", {}):
                    if field == "body":
                        body_fields = {k: v for k, v in problema.items() if k not in ["error_message", "id", "system_id"]}
                        params["body"] = {**body_fields, **hit["params"]}
                    elif field in problema:
                        params[field] = problema[field]
                    elif field in hit["params"]:
                        params[field] = hit["params"][field]
            else:
                system_fields = {k: v for k, v in problema.items() if k != "error_message"}
                if "system_id" in system_fields:
                    params["system_id"] = str(system_fields["system_id"])
                elif "id" in system_fields:
                    params["system_id"] = str(system_fields["id"])
                body_fields = {k: v for k, v in system_fields.items() if k not in ["id", "system_id"]}
                params["body"] = {**body_fields, **hit["params"]}

            print(f"[Agent] Parâmetros finais para execução: {params}")
            exec_out = mcp_execute_action(client_id, hit["action"], params)
            run_log.append({"step": "execute", "action": hit["action"], "params": params, "output": exec_out})

            time.sleep(1)
            cycle += 1

        print(f"[Agent] Resultado final: {{'result': 'unresolved', 'log': run_log}}")
        return {"result": "unresolved", "log": run_log}


if __name__ == "__main__":
    print("[Agent] Script iniciado!")
    payload = {"client_id": CLIENT_ID}
    result = agent_run(payload)
    print("[Agent] Resultado final:", result)