class ToolRegistry:
    def __init__(self, server, tool_loader):
        self.server = server
        self.tool_loader = tool_loader

    def register_all_tools(self):
        # Simples: apenas printa os nomes das ferramentas
        for name in self.tool_loader.list_tool_names():
            print(f"[MCP Server] Registrando ferramenta: {name}")
        # Aqui seria o ponto para registrar endpoints reais no server
