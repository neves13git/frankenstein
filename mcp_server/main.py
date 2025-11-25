"""
MCP Server - Adaptador Universal para Ferramentas
Carrega dinamicamente ferramentas de YAMLs (OpenAPI, formato customizado) e expõe via MCP.
"""
import asyncio
import sys
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from tool_loader import ToolLoader
from tool_registry import ToolRegistry

# Inicializar servidor MCP
server = Server("frankenstein-mcp")

# Inicializar carregador de ferramentas
tool_loader = ToolLoader(base_url="http://localhost:9000")

# Inicializar registro de ferramentas
tool_registry = ToolRegistry(server, tool_loader)

# Carregar ferramentas de YAMLs
def load_tools():
    """Carrega todas as ferramentas dos diretórios configurados."""
    # Carregar do diretório atual (openapi.yaml)
    current_dir = Path(__file__).parent
    tools = tool_loader.load_from_directory(str(current_dir))
    
    # Carregar do diretório de tools do system_simulator (se existir)
    tools_dir = current_dir.parent / "system_simulator" / "tools"
    if tools_dir.exists():
        tools.update(tool_loader.load_from_directory(str(tools_dir)))
    
    # Registrar todas as ferramentas no loader
    tool_loader.tools.update(tools)
    
    print(f"[MCP Server] Carregadas {len(tools)} ferramentas de YAMLs")
    return tools

# Carregar ferramentas na inicialização
loaded_tools = load_tools()

# Registrar dinamicamente todas as ferramentas carregadas
tool_registry.register_all_tools()

async def main():
    """Inicia o servidor MCP."""
    print("[MCP Server] Iniciando servidor...")
    print(f"[MCP Server] Ferramentas disponíveis: {', '.join(tool_loader.list_tool_names())}")
    
    async with stdio_server() as (read_stream, write_stream):
        from mcp.server.lowlevel.server import NotificationOptions
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frankenstein-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
