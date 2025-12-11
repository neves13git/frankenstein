"""
Nó LangGraph: faz o scan dos sistemas via MCP.
LLM decide qual ferramenta usar e quais argumentos passar (100% cognitivo).
"""
import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def scan_node(state):
    """
    Recebe o estado, executa o scan via MCP e devolve o novo estado.
    Agora a escolha da ferramenta é feita pelo LLM.
    """
    print("\n" + "="*60)
    print("🔍 [SCAN NODE] Iniciando scan...")
    print("="*60)
    
    mcp_client = state["mcp_client"]
    client_id = state["client_id"]
    
    print(f"📡 A conectar ao MCP Server...")
    await mcp_client.initialize({"session_id": f"sim-session-{client_id}"})
    
    print(f"🛠️  A obter lista de ferramentas do MCP...")
    tools_resp = await mcp_client.list_tools()
    print(f"📦 Resposta do MCP: {tools_resp}")
    
    tools = tools_resp.get("result", [])
    state["tools"] = tools
    
    print(f"✅ Total tools obtained: {len(tools)}")
    if tools:
        print(f"\n📋 Available tools:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.get('name')} - {tool.get('description', 'No description')}")
    else:
        print(f"⚠️  WARNING: No tools obtained from MCP!")
        print(f"   Check if MCP Server is running at: {mcp_client.base_url}")
        state["scan_error"] = "Nenhuma ferramenta disponível no MCP"
        return state

    # Preparar prompt para o LLM - TOTALMENTE GENÉRICO
    tool_descriptions = "\n".join([
        f"Nome: {t['name']}\nDescrição: {t.get('description', '')}\nInputSchema: {t.get('inputSchema', {})}" for t in tools
    ])
    
    # Contexto dinâmico baseado no estado
    context_info = f"Contexto disponível: client_id={client_id}" if client_id else "Sem contexto específico"
    
    prompt = (
        "Você é um agente inteligente que precisa escolher a ferramenta certa para obter dados.\n\n"
        f"{context_info}\n\n"
        "Ferramentas disponíveis:\n"
        f"{tool_descriptions}\n\n"
        "TAREFA: Escolhe a ferramenta mais adequada para obter/listar dados relevantes ao contexto fornecido.\n"
        "Se há um id de cliente, escolhe ferramentas que permitam filtrar por esse ID.\n"
        "Se não há contexto específico, escolhe ferramentas que listem dados gerais.\n\n"
        "RESPOSTA: Apenas o nome exato da ferramenta (sem explicações)."
    )

    # Chamar o LLM (OpenAI) - nova API
    print(f"\n🤖 Asking LLM which tool to use...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um agente especialista em escolher ferramentas apropriadas baseado em contexto e descrições. Retorna APENAS o nome da ferramenta, sem explicações."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=50,
            temperature=0
        )
        scan_tool_name = response.choices[0].message.content.strip()
        print(f"✅ LLM decidiu usar a ferramenta: '{scan_tool_name}'")
    except Exception as e:
        state["scan_result"] = None
        state["scan_error"] = f"Erro ao consultar LLM: {e}"
        print(f"❌ [SCAN NODE] Erro LLM: {e}")
        return state

    # Encontrar a ferramenta pelo nome devolvido pelo LLM
    scan_tool = next((t for t in tools if t["name"] == scan_tool_name), None)
    if not scan_tool:
        state["scan_result"] = None
        state["scan_error"] = f"LLM devolveu nome inválido: {scan_tool_name}"
        print(f"❌ Tool '{scan_tool_name}' not found in MCP list!")
        return state
    
    print(f"✅ Tool found in MCP!")

    # GENÉRICO: LLM decide os argumentos baseado no inputSchema
    input_schema = scan_tool.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required_params = input_schema.get("required", [])
    
    # Preparar contexto disponível no state
    available_context = {
        "client_id": client_id
    }
    
    if properties:
        # Perguntar ao LLM quais argumentos passar
        args_prompt = f"""
Ferramenta escolhida: {scan_tool['name']}
InputSchema: {json.dumps(input_schema, indent=2)}

Contexto disponível:
{json.dumps(available_context, indent=2)}

TAREFA: Determina quais argumentos passar para esta ferramenta baseado no schema e no contexto disponível.
Se o schema requer "client_id" e há client_id disponível, inclui-o.
Se há outros parâmetros opcionais relevantes, considera-os.

RESPOSTA: JSON com os argumentos (ex: {{"client_id": 1}}) ou {{}} se não há argumentos necessários.
"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": args_prompt}],
                max_tokens=150,
                temperature=0
            )
            args_text = response.choices[0].message.content.strip()
            if args_text.startswith("```"):
                args_text = args_text.split("```")[1].strip()
                if args_text.startswith("json"):
                    args_text = args_text[4:].strip()
            scan_args = json.loads(args_text)
            print(f"🧠 LLM decided arguments: {scan_args}")
        except Exception as e:
            print(f"⚠️  Error determining arguments via LLM: {e}")
            # Fallback: usar apenas parâmetros required que existem no contexto
            scan_args = {k: v for k, v in available_context.items() if k in required_params}
    else:
        scan_args = {}
    
    if scan_args:
        print(f"📤 Chamando ferramenta '{scan_tool['name']}' com argumentos: {scan_args}")
    else:
        print(f"📤 Chamando ferramenta '{scan_tool['name']}' sem argumentos")
    
    print(f"⏳ Executando scan via MCP...")
    scan_result = await mcp_client.call_tool(scan_tool['name'], scan_args)
    
    print(f"✅ Scan executado com sucesso!")
    print(f"📊 Resultado: {scan_result}")
    
    state["scan_result"] = scan_result
    return state
