import yaml
import json
from pathlib import Path
from mcp.types import Tool
from typing import Any, Dict, List

def load_openapi_spec(filepath: str) -> Dict[str, Any]:
    """
    Loads an OpenAPI/Swagger specification from a YAML or JSON file.
    - Accepts a file path.
    - Returns the parsed spec as a Python dictionary.
    - Raises an error if the file does not exist or is not YAML/JSON.
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI spec not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

def generate_mcp_tools(spec: Dict[str, Any]) -> List[Tool]:
    """
    Generates a list of MCP Tool objects from an OpenAPI specification.
    - Iterates over all paths and HTTP methods in the spec.
    - For each operation, builds a Tool with:
        - name: from operationId or method/path
        - description: from summary or description
        - inputSchema: built from parameters and requestBody
    - Stores HTTP method, path, and base_url as metadata for later use.
    - Returns the list of Tool objects.
    """
    tools = []
    base_url = spec.get('servers', [{}])[0].get('url', 'http://localhost:9000')
    
    paths = spec.get('paths', {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue
            
            # Generate tool name
            operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
            tool_name = operation_id.replace(' ', '_').lower()
            
            # Generate description
            description = operation.get('summary', operation.get('description', f"{method.upper()} {path}"))
            
            # Build input schema from parameters and request body
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # Path/query parameters
            parameters = operation.get('parameters', [])
            for param in parameters:
                param_name = param.get('name')
                param_schema = param.get('schema', {})
                param_type = param_schema.get('type', 'string')
                
                input_schema['properties'][param_name] = {
                    "type": param_type,
                    "description": param.get('description', '')
                }
                
                if param.get('required', False):
                    input_schema['required'].append(param_name)
            
            # Request body (for POST/PUT)
            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json', {})
                body_schema = json_content.get('schema', {})
                
                if body_schema:
                    input_schema['properties']['body'] = body_schema
                    if request_body.get('required', False):
                        input_schema['required'].append('body')
            
            # Create the Tool object
            tool = Tool(
                name=tool_name,
                description=description,
                inputSchema=input_schema
            )
            
            # Store metadata for later use (HTTP method, path, base_url)
            tool._metadata = {
                'method': method.upper(),
                'path': path,
                'base_url': base_url
            }
            
            tools.append(tool)
    
    return tools

def get_tool_metadata(tool: Tool) -> Dict[str, Any]:
    import yaml
import json
from pathlib import Path
from mcp.types import Tool
from typing import Any, Dict, List

def load_openapi_spec(filepath: str) -> Dict[str, Any]:
    """
    Loads an OpenAPI/Swagger specification from a YAML or JSON file.
    - Accepts a file path.
    - Returns the parsed spec as a Python dictionary.
    - Raises an error if the file does not exist or is not YAML/JSON.
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI spec not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

def generate_mcp_tools(spec: Dict[str, Any]) -> List[Tool]:
    """
    Generates a list of MCP Tool objects from an OpenAPI specification.
    - Iterates over all paths and HTTP methods in the spec.
    - For each operation, builds a Tool with:
        - name: from operationId or method/path
        - description: from summary or description
        - inputSchema: built from parameters and requestBody
    - Stores HTTP method, path, and base_url as metadata for later use.
    - Returns the list of Tool objects.
    """
    tools = []
    base_url = spec.get('servers', [{}])[0].get('url', 'http://localhost:9000')
    
    paths = spec.get('paths', {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue
            
            # Generate tool name
            operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
            tool_name = operation_id.replace(' ', '_').lower()
            
            # Generate description
            description = operation.get('summary', operation.get('description', f"{method.upper()} {path}"))
            
            # Build input schema from parameters and request body
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # Path/query parameters
            parameters = operation.get('parameters', [])
            for param in parameters:
                param_name = param.get('name')
                param_schema = param.get('schema', {})
                param_type = param_schema.get('type', 'string')
                
                input_schema['properties'][param_name] = {
                    "type": param_type,
                    "description": param.get('description', '')
                }
                
                if param.get('required', False):
                    input_schema['required'].append(param_name)
            
            # Request body (for POST/PUT)
            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json', {})
                body_schema = json_content.get('schema', {})
                
                if body_schema:
                    input_schema['properties']['body'] = body_schema
                    if request_body.get('required', False):
                        input_schema['required'].append('body')
            
            # Create the Tool object
            tool = Tool(
                name=tool_name,
                description=description,
                inputSchema=input_schema
            )
            
            # Store metadata for later use (HTTP method, path, base_url)
            tool._metadata = {
                'method': method.upper(),
                'path': path,
                'base_url': base_url
            }
            
            tools.append(tool)
    
    return tools

def get_tool_metadata(tool: Tool) -> Dict[str, Any]:
    """
    Returns the metadata dictionary for a given Tool object.
    - Used to retrieve HTTP method, path, and base_url for API calls.
    """
    return getattr(tool, '_metadata', {})