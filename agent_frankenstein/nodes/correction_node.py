# nodes/correction_node.py

from typing import Dict
import json

async def correction_node(state: Dict) -> Dict:
    """
    Executa as correções sugeridas pelo LLM/RAG.
    """
    print("\n" + "="*60)
    print("🔧 [CORRECTION NODE] Executando correções...")
    print("="*60)
    
    rag_info = state.get("rag_info", {})
    mcp_client = state["mcp_client"]
    tools = state.get("tools", [])
    
    if not rag_info:
        print("⚠️  No corrections to execute!")
        state["correction_result"] = None
        return state
    
    correction_results = {}
    
    for problem_id, solution in rag_info.items():
        recommended_tool = solution.get("recommended_tool")
        tool_args = solution.get("tool_args", {})
        reasoning = solution.get("reasoning", "N/A")
        
        if not recommended_tool:
            print(f"\n⚠️  No tool recommended for problem: {problem_id}")
            correction_results[problem_id] = {
                "success": False,
                "error": "Nenhuma ferramenta recomendada"
            }
            continue
        
        print(f"\n🔧 Problem: {problem_id}")
        print(f"   🛠️  Recommended tool: {recommended_tool}")
        print(f"   📝 Reasoning: {reasoning}")
        print(f"   📋 Arguments: {json.dumps(tool_args, indent=2)}")
        
        # Se é uma correção de sistema inativo, garantir que também limpa a error_message
        if recommended_tool == "update_system_by_id" and "body" in tool_args:
            body = tool_args["body"]
            # Se está ativando o sistema, limpar a mensagem de erro
            if body.get("is_active") is True:
                if "error_message" not in body:
                    body["error_message"] = ""
                    tool_args["body"] = body
                    print(f"   🧹 Clearing error_message when activating system")
        
        # Procurar tool no MCP
        tool_exists = any(t["name"] == recommended_tool for t in tools)
        
        if tool_exists:
            try:
                print(f"   ⏳ Executando {recommended_tool}...")
                result = await mcp_client.call_tool(recommended_tool, tool_args)
                
                print(f"   📊 Resposta do MCP: {result}")
                
                if result.get("error"):
                    correction_results[problem_id] = {
                        "success": False,
                        "tool": recommended_tool,
                        "error": result["error"]
                    }
                    print(f"   ❌ Erro na correção: {result['error']}")
                else:
                    correction_results[problem_id] = {
                        "success": True,
                        "tool": recommended_tool,
                        "result": result.get("result")
                    }
                    print(f"   ✅ Correção executada com sucesso!")
                    
            except Exception as e:
                correction_results[problem_id] = {
                    "success": False,
                    "tool": recommended_tool,
                    "error": str(e)
                }
                print(f"   ❌ Exception executing correction: {e}")
        else:
            correction_results[problem_id] = {
                "success": False,
                "tool": recommended_tool,
                "error": f"Tool '{recommended_tool}' não encontrada no MCP"
            }
            print(f"   ⚠️  Tool not found in MCP!")
    
    state["correction_result"] = correction_results
    state["correction_attempts"] = state.get("correction_attempts", 0) + 1
    return state