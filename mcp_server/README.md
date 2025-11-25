# MCP Server - Adaptador Universal para Ferramentas

Este MCP Server carrega dinamicamente ferramentas a partir de arquivos YAML, suportando múltiplos formatos:
- **OpenAPI/Swagger**: Especificações de APIs REST
- **Formato Customizado**: YAMLs com estrutura `tools:`
- **Funções Python**: Funções locais (futuro)

## Estrutura

```
mcp_server/
├── main.py              # Servidor MCP principal
├── tool_loader.py       # Carregador de ferramentas de YAMLs
├── tool_registry.py     # Registro dinâmico de ferramentas no MCP
├── codegen.py           # Gerador de funções a partir de OpenAPI (legado)
├── openapi.yaml         # Especificação OpenAPI da API do System Simulator
└── requirements.txt     # Dependências
```

## Como Funciona

1. **Carregamento**: O `tool_loader.py` lê todos os YAMLs dos diretórios configurados
2. **Conversão**: Cada endpoint/função é convertido em uma função Python assíncrona
3. **Registro**: O `tool_registry.py` registra cada ferramenta no servidor MCP
4. **Exposição**: O servidor MCP expõe todas as ferramentas para o LLM/Agent

## Formato YAML - OpenAPI

O servidor suporta especificações OpenAPI 3.0. Exemplo:

```yaml
openapi: 3.0.0
info:
  title: Minha API
  version: 1.0.0
servers:
  - url: http://localhost:9000
paths:
  /api/v1/system1/{client_id}:
    get:
      summary: Lista sistemas de um cliente
      operationId: get_client_systems
      parameters:
        - name: client_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Sucesso
```

**Características importantes:**
- `operationId`: Nome da ferramenta (obrigatório ou será gerado)
- `summary`: Descrição da ferramenta
- `parameters`: Parâmetros de path, query ou body
- `requestBody`: Parâmetros do corpo da requisição

## Formato YAML - Customizado

Formato alternativo para ferramentas que não são APIs REST:

```yaml
tools:
  - name: minha_ferramenta
    description: Descrição da ferramenta
    input_schema:
      type: object
      properties:
        param1:
          type: string
          description: Descrição do parâmetro
      required: [param1]
    output_schema:
      type: object
      properties:
        resultado:
          type: string
    # Opção 1: URL HTTP
    url: http://localhost:9000/api/endpoint
    method: POST
    # Opção 2: Função Python (futuro)
    # python_function: meu_modulo.minha_funcao
    examples:
      - input:
          param1: "valor exemplo"
        output:
          resultado: "sucesso"
```

## Adicionar Novas Ferramentas

### Método 1: Adicionar YAML OpenAPI

1. Crie um arquivo `nova_api.yaml` no diretório `mcp_server/` ou `system_simulator/tools/`
2. Defina os endpoints seguindo o formato OpenAPI
3. Reinicie o servidor MCP
4. As ferramentas serão carregadas automaticamente

### Método 2: Adicionar YAML Customizado

1. Crie um arquivo `minhas_ferramentas.yaml` no diretório `system_simulator/tools/`
2. Use o formato customizado descrito acima
3. Reinicie o servidor MCP

## Executar o Servidor

```bash
cd mcp_server
pip install -r requirements.txt
python main.py
```

O servidor MCP usa stdio (entrada/saída padrão) para comunicação, então normalmente é executado por um cliente MCP.

## Integração com Agent

O agent cognitivo pode consultar as ferramentas disponíveis e executá-las através do protocolo MCP. Veja `../agents/agent.py` para exemplo de integração.

## Debugging

Para ver quais ferramentas foram carregadas, o servidor imprime no início:
```
[MCP Server] Carregadas X ferramentas de YAMLs
[MCP Server] Ferramentas disponíveis: tool1, tool2, ...
```

## Próximos Passos

- [ ] Suporte para funções Python locais
- [ ] Validação de schemas de entrada
- [ ] Cache de resultados
- [ ] Autenticação/autorização
- [ ] Rate limiting
