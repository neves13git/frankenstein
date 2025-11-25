import yaml
import requests

def load_openapi_and_generate_functions(filepath):

    with open(filepath, "r") as f:
        spec = yaml.safe_load(f)
    tools = []
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            name = details.get("operationId") or f"{method}_{path.replace('/', '_')}"
            name = name.replace("{", "").replace("}", "").replace("-", "_")
            params = {}
            # Path parameters
            if "parameters" in details:
                for p in details["parameters"]:
                    param_type = p.get("schema", {}).get("type", "string")
                    params[p["name"]] = {"type": param_type, "in": p["in"]}
            # Body parameters
            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                app_json = content.get("application/json", {})
                schema = app_json.get("schema", {})
                for k, v in schema.get("properties", {}).items():
                    params[k] = {"type": v.get("type", "string"), "in": "body"}
            def make_func(path=path, method=method, params=params):
                def func(**kwargs):
                    url = "http://localhost:9000" + path
                    # Substituir parâmetros de path
                    for pname, pinfo in params.items():
                        if pinfo.get("in") == "path" and pname in kwargs:
                            url = url.replace("{" + pname + "}", str(kwargs[pname]))
                    # Body
                    body = {k: v for k, v in kwargs.items() if params.get(k, {}).get("in") == "body"}
                    # Query (não implementado, mas pode ser adicionado)
                    resp = requests.request(method.upper(), url, json=body if body else None)
                    return resp.json()
                return func
            tools.append({
                "name": name,
                "description": details.get("summary", f"Call {method} {path}"),
                "schema": params,
                "callable": make_func()
            })
    return tools
