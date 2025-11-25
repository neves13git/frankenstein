import httpx
from typing import Any, Dict

# Global dictionary to store metadata for each tool (endpoint)
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

async def execute_api_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Executes an HTTP call to the API corresponding to the tool.
    - Receives the tool name (tool_name) and the arguments provided by the user.
    - Looks up the tool's metadata (HTTP method, path, base_url) in TOOL_REGISTRY.
    - Substitutes path parameters in the URL.
    - Separates the body (body) from query parameters.
    - Makes the HTTP call using httpx and returns the response as text.
    """
    # Get the tool's metadata
    metadata = TOOL_REGISTRY.get(tool_name, {})
    
    if not metadata:
        raise ValueError(f"Tool {tool_name} not found in registry")
    
    method = metadata.get('method', 'GET')
    path = metadata.get('path', '/')
    base_url = metadata.get('base_url', 'http://localhost:9000')
    
    # Build the URL, replacing path parameters (e.g., {client_id})
    url = base_url + path
    arguments_copy = arguments.copy()
    
    for key, value in list(arguments_copy.items()):
        if f"{{{key}}}" in url:
            url = url.replace(f"{{{key}}}", str(value))
            del arguments_copy[key]
    
    # Separate the body from query parameters
    body = arguments_copy.pop('body', None)
    query_params = arguments_copy
    
    # Make the HTTP call according to the method
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == 'GET':
                response = await client.get(url, params=query_params)
            elif method == 'POST':
                response = await client.post(url, json=body, params=query_params)
            elif method == 'PUT':
                response = await client.put(url, json=body, params=query_params)
            elif method == 'DELETE':
                response = await client.delete(url, params=query_params)
            elif method == 'PATCH':
                response = await client.patch(url, json=body, params=query_params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            return f"HTTP Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

def register_tool_metadata(tool_name: str, metadata: Dict[str, Any]):
    """
    Registers the metadata of a tool in the global TOOL_REGISTRY dictionary.
    - Used at server startup to associate each tool with its endpoint/method.
    """
    TOOL_REGISTRY[tool_name] = metadata