"""
Cliente utilitário para comunicação com o MCP via JSON-RPC.
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/rpc")

class MCPClient:
    def __init__(self, base_url=MCP_SERVER_URL):
        self.base_url = base_url
        self.session_id = None
        self._id = 1

    async def initialize(self, client_info=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "initialize",
            "params": {"clientInfo": client_info or {"session_id": "sim-session"}}
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.base_url, json=payload)
            self.session_id = payload["params"]["clientInfo"]["session_id"]
            self._id += 1
            return resp.json()

    async def list_tools(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/list"
        }
        headers = {"x-session-id": self.session_id}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            self._id += 1
            return resp.json()

    async def call_tool(self, tool_name, arguments):
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        headers = {"x-session-id": self.session_id}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            self._id += 1
            return resp.json()
