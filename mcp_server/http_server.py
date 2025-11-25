# http_server.py - MCP Server HTTP (FastAPI)
from fastapi import FastAPI, Request
from pydantic import BaseModel
from codegen import load_openapi_spec, generate_mcp_tools, get_tool_metadata
from api_client import execute_api_call, register_tool_metadata
from mcp.types import Tool, TextContent
import uvicorn

app = FastAPI()

# Global list to store all generated Tool objects
GENERATED_TOOLS = []

class CallToolRequest(BaseModel):
    name: str
    arguments: dict = {}

@app.on_event("startup")
def startup_event():
    global GENERATED_TOOLS
    spec = load_openapi_spec("openapi.yaml")
    GENERATED_TOOLS = generate_mcp_tools(spec)
    for tool in GENERATED_TOOLS:
        metadata = get_tool_metadata(tool)
        register_tool_metadata(tool.name, metadata)

@app.get("/tools")
def list_tools():
    return {"tools": [tool.name for tool in GENERATED_TOOLS]}

@app.post("/call_tool")
async def call_tool(req: CallToolRequest):
    tool_config = next((t for t in GENERATED_TOOLS if t.name == req.name), None)
    if not tool_config:
        return {"status": "error", "message": f"Tool {req.name} not found"}
    try:
        result = await execute_api_call(req.name, req.arguments)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("http_server:app", host="0.0.0.0", port=9100, reload=True)
