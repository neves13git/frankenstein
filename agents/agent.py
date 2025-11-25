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
    {"symptom": "erro de conexão", "procedure": "Reiniciar módulo de rede", "action": "restart_module", "params": {"module": "network"}},
    {"symptom": "sistema inativo", "procedure": "Verificar alimentação elétrica", "action": "check_power", "params": {}},
]


def mcp_get_tools():
    """Busca a lista de ferramentas disponíveis no servidor MCP."""
    try:
        r = requests.get(f"{MCP_SERVER_URL}/tools")
        r.raise_for_status()
        return r.json()["tools"]
    except HTTPError as e:
        print(f"[Agent] ERRO HTTP ao obter ferramentas: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Agent] ERRO de Conexão ao obter ferramentas: {e}")
        return []


def mcp_get_systems(client_id):
    """
    Busca o status dos sistemas do cliente (System Simulator).
    """
    # Usar SYSTEM_SIMULATOR_URL para montar a URL base.
    url = f"{SYSTEM_SIMULATOR_URL}/api/v1/system1/{client_id}"
    try:
        r = requests.get(url)
        r.raise_for_status()
        
        # Assume-se que o endpoint retorna uma LISTA de sistemas diretamente.
        return r.json()
        
    except HTTPError as e:
        # Captura o erro 500 ou qualquer outro erro HTTP
        print(f"[Agent] ERRO HTTP ao obter sistemas ({e.response.status_code}): {e}")
        return []
    except requests.exceptions.RequestException as e:
        # Captura erros de rede (ex: servidor não está rodando)
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

    for cycle in range(max_cycles):
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

        # Só busca procedimentos (RAG) se houver problemas
        for problema in problemas:
            symptom_text = problema.get("error_message") or "sistema inativo"
            hit = next((d for d in docs if d["symptom"] in symptom_text), None)
            run_log.append({"step": "rag_search", "symptom": symptom_text, "hit": hit})

            if not hit:
                print(f"[Agent] Nenhum procedimento encontrado para sintoma: {symptom_text}")
                continue

            exec_out = mcp_execute_action(client_id, hit["action"], hit["params"])
            run_log.append({"step": "execute", "action": hit["action"], "params": hit["params"], "output": exec_out})

        time.sleep(1)

    return {"result": "unresolved", "log": run_log}

if __name__ == "__main__":
    # Exemplo de entrada
    payload = {"client_id": CLIENT_ID}
    result = agent_run(payload)
    print("[Agent] Resultado final:", result)