from fastapi import FastAPI
from tool_loader import ToolLoader
from tool_registry import ToolRegistry
from pathlib import Path

app = FastAPI(title="MCP Server - Mock Tools API")

# Inicializar carregador e registrar ferramentas
tool_loader = ToolLoader()
tools = tool_loader.load_from_directory(str(Path(__file__).parent))
tool_loader.tools.update(tools)
tool_registry = ToolRegistry(None, tool_loader)
tool_registry.register_all_tools()

@app.get("/tools")
def list_tools():
    """Lista os nomes das ferramentas carregadas."""
    return {"tools": tool_loader.list_tool_names()}

@app.get("/tools/{tool_name}")
def get_tool(tool_name: str):
    """Retorna o conteúdo YAML da ferramenta."""
    tool = tool_loader.tools.get(tool_name)
    if not tool:
        return {"error": "Tool not found"}
    return tool


# Endpoint para executar ações (mock)
from fastapi import Request

@app.post("/execute")
async def execute_action(request: Request):
    payload = await request.json()
    client_id = payload.get("client_id")
    action = payload.get("action")
    params = payload.get("params", {})
    print(f"[MCP Server] Executando ação '{action}' para client_id={client_id} com params={params}")
    # Simula sucesso
    return {"status": "ok", "action": action, "params": params}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_mcp_server:app", host="0.0.0.0", port=9100, reload=True)
