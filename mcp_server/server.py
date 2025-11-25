import asyncio
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types
from codegen import load_openapi_spec, generate_mcp_tools, get_tool_metadata
from api_client import execute_api_call, register_tool_metadata

# Initialize the MCP server instance
server = Server("frankenstein-mcp-server")

# Global list to store all generated Tool objects
GENERATED_TOOLS = []

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    Handler for listing all available tools.
    Called when a client requests the list of tools.
    Returns the list of Tool objects generated from the OpenAPI spec.
    """
    return GENERATED_TOOLS

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """
    Handler for executing a tool (API call) by name.
    - Receives the tool name and arguments from the client.
    - Finds the corresponding Tool object.
    - Calls the API using execute_api_call and returns the result as TextContent.
    """
    if arguments is None:
        arguments = {}
    
    # Find the tool configuration by name
    tool_config = next((t for t in GENERATED_TOOLS if t.name == name), None)
    
    if not tool_config:
        raise ValueError(f"Tool {name} not found")
    
    # Execute the API call and return the result
    try:
        result = await execute_api_call(name, arguments)
        return [TextContent(
            type="text",
            text=f"API call successful:\n{result}"
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing API call: {str(e)}"
        )]

async def main():
    """
    Main entry point for the MCP server.
    - Loads the OpenAPI spec.
    - Generates the list of Tool objects.
    - Registers each tool's metadata for later API execution.
    - Starts the MCP server using stdio.
    """
    global GENERATED_TOOLS
    
    # Load OpenAPI spec and generate tools
    import sys
    print("🔄 Loading OpenAPI specification...", file=sys.stderr)
    spec = load_openapi_spec("openapi.yaml")
    
    print("🛠️ Generating MCP tools from OpenAPI spec...", file=sys.stderr)
    GENERATED_TOOLS = generate_mcp_tools(spec)
    
    # Register metadata for each tool (for use in API calls)
    for tool in GENERATED_TOOLS:
        metadata = get_tool_metadata(tool)
        register_tool_metadata(tool.name, metadata)
    
    print(f"✅ Generated {len(GENERATED_TOOLS)} tools", file=sys.stderr)
    for tool in GENERATED_TOOLS:
        print(f"  - {tool.name}: {tool.description}", file=sys.stderr)
    
    # Start the MCP server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frankenstein-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    # Entry point: runs the main async function
    asyncio.run(main())