import os
import yaml
from pathlib import Path

class ToolLoader:
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.tools = {}

    def load_from_directory(self, directory):
        tools = {}
        for file in Path(directory).glob("*.yaml"):
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # Simples: usa o nome do arquivo como nome da ferramenta
                tool_name = file.stem
                tools[tool_name] = data
        return tools

    def list_tool_names(self):
        return list(self.tools.keys())
