
## Cognitive Agent para Diagnóstico e Correção Automatizada

### 1) Arquitetura Proposta (Visão Geral)

**Entrada:** JSON client_info com client_id, telemetria, logs e parâmetros contextuais.

**Agent principal (LangChain / LangGraph Runnable):** Recebe o JSON e decide os passos diagnósticos. Mantém o loop: Diagnosticar → RAG (buscar procedimentos) → Executar via MCP → Verificar resultado → Repetir até ok. (stateful workflow).

**Tool layer:** Conjunto de tools (wrappers HTTP) que chamam o MCP Server para operações (diagnóstico, executar ação X, recolher estado). O MCP expõe APIs via YAML (OpenAPI) — as tools mapeiam endpoints para chamadas HTTP autenticadas.

**RAGstore:** PostgreSQL com extensão pgvector contendo embeddings dos PDFs (sintomas, procedimentos, ações). Quando o agent detecta sintomas, faz busca por similaridade e obtém procedimentos associados.

**LLM & Chain:** LLM (OpenAI/Anthropic/whatever) para: interpretar JSON, decidir quais ferramentas MCP chamar, analisar outputs, e gerar instruções para procedimentos corretivos.



**Diagrama mental (texto):**
JSON -> Agent (runnable) -> decide -> Tool(MCP) call -> MCP response -> if issue -> Retriever(pgvector) -> procedures -> Agent -> Tool(MCP) execute -> loop -> final message

---

### 2) Fluxo de Execução Detalhado (Pseudopassos)

1. Receber JSON (contém client_id).
2. Pre-check: validar formato, extrair métricas (ex.: error_codes, sensor_values).
3. Diagnóstico inicial: chamar MCP diagnostic API (via Tool) com client_id. Receber output (status/metrics/logs).
4. LLM análise: LLM interpreta output MCP e gera “sintomas” (texto curado).
5. RAG: consulta pgvector com embedding do sintoma; recuperar top-k documentos/procedures (pdf snippets).
6. Decisão de ação: se similaridade acima de threshold e existir procedimento, escolher ação corretiva e chamar MCP para executar. Se não existir match, marcar como “escalate” → (no futuro: abrir chat WhatsApp).
7. Verificação: após executar ação, chamar MCP para re-check; se problema persiste, repetir ciclo; se resolvido, terminar e retornar resumo.


---

### 3) Componentes Concretos e Escolhas Tecnológicas

- **LangChain / LangGraph:** Para criar Runnables / workflows stateful (graph-based agents).
- **LangServe:** Para expor o agente como serviço HTTP.

- **Postgres + pgvector:** Armazenamento de vetores para RAG.
- **LLM:** Provider à escolha (OpenAI, Anthropic, local LLM).
- **HTTP tools:** Wrappers que convertem chamadas do agente em POST/GET para MCP.

---

### 4) Exemplo de Implementação — Esqueleto em Python (LangChain style)

```python
import requests
from langchain_core.runnables import RunnableLambda
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import PGVector
from langchain.chat_models import ChatOpenAI
import time

# Config
MCP_BASE = "https://mcp.example.com/api"
MCP_TOKEN = "..."           # usar secret manager
PG_CONN = "postgresql://user:pass@pg-host:5432/mydb"
EMBED_MODEL = "text-embedding-3-small"  # exemplo OpenAI
LLM_MODEL = "gpt-4o-mini"               # exemplo

# Tools (wrappers HTTP)
def mcp_call(endpoint: str, payload: dict, method="POST"):
   headers = {"Authorization": f"Bearer {MCP_TOKEN}", "Content-Type":"application/json"}
   url = f"{MCP_BASE}/{endpoint}"
   r = requests.request(method, url, json=payload, headers=headers, timeout=30)
   r.raise_for_status()
   return r.json()

def mcp_diagnose(client_id: str):
   return mcp_call("diagnose", {"client_id": client_id})

def mcp_execute_action(client_id: str, action_name: str, params: dict):
   return mcp_call("execute", {"client_id": client_id, "action": action_name, "params": params})

def mcp_check(client_id: str):
   return mcp_call("status", {"client_id": client_id})

# RAG setup (pgvector)
embedder = OpenAIEmbeddings(model=EMBED_MODEL, openai_api_key="...")
pgstore = PGVector.from_documents(
   docs=[], embedding=embedder, connection_string=PG_CONN, collection_name="kb_procedures"
)

# LLM setup
llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

# Agent runnable (simplified loop)
def agent_run(json_input: dict):
   client_id = json_input["client_id"]
   run_log = []
   max_cycles = 6

   for cycle in range(max_cycles):
      diag = mcp_diagnose(client_id)
      run_log.append({"step":"diagnose", "output":diag})

      prompt = f"""Recebeste este resultado do diagnóstico para client {client_id}:
{diag}
Extrai um resumo curto (1-2 linhas) com o sintoma principal e lista possíveis keywords."""
      symptom_resp = llm.chat([{"role":"user","content":prompt}])
      symptom_text = symptom_resp.content
      run_log.append({"step":"llm_symptom", "output":symptom_text})

      query_emb = embedder.embed_query(symptom_text)
      hits = pgstore.similarity_search_by_vector(query_emb, k=5)
      run_log.append({"step":"rag_hits", "output":[h.page_content for h in hits]})

      if not hits:
         run_log.append({"step":"escalate", "reason":"no_procedure_found"})
         break

      top_doc = hits[0].page_content
      prompt_actions = f"Com base no sintoma: {symptom_text} e no procedimento: {top_doc}, devolve o nome da ação a executar e parâmetros em JSON."
      action_resp = llm.chat([{"role":"user","content":prompt_actions}])
      try:
         action_json = eval(action_resp.content)  # substituir por json.loads/clean parsing
      except Exception:
         run_log.append({"step":"parse_error","content": action_resp.content})
         break

      exec_out = mcp_execute_action(client_id, action_json["action"], action_json.get("params", {}))
      run_log.append({"step":"execute", "action": action_json, "output": exec_out})

      check = mcp_check(client_id)
      run_log.append({"step":"check", "output":check})
      if check.get("status") == "ok":
         return {"result":"resolved", "log": run_log}
      else:
         time.sleep(1)

   return {"result":"escalated_or_unresolved", "log": run_log}

agent_runnable = RunnableLambda(lambda payload: agent_run(payload))
# depois expor com LangServe / FastAPI (ex.: app.post("/run") -> agent_runnable.run(payload))
```

**Pontos importantes:**
- Segurança: nunca eval em produção; usar json.loads com validação JSON Schema.
- Retries/timeouts: implementar circuit breakers e backoff nas chamadas MCP.


---

### 5) Como construir a RAG em Postgres + pgvector (Resumo Prático)

- Instalar pgvector no Postgres (Docker image pgvector/pgvector).
- Extrair texto dos PDFs (pdfminer / tika / pypdf) e dividir em chunks (512–1.000 tokens).
- Gerar embeddings para cada chunk e inserir numa tabela com vector col.
- Indexar com ivfflat / hnsw para consultas rápidas.
- Criar metadados (tipo: sintoma/procedimento/ação, score_confidence, origem_pdf, page).
- Usar PGVector integration do LangChain para similarity_search e recuperar documentos relevantes.

---

### 6) Design do Loop de Decisão (Heurísticas / Thresholds)

- Threshold similarity: usar um limiar inicial (ex: 0.75 cosine) — calibrar com validação.
- Confiança LLM: validar ações com regras (whitelist de actions permitidas) antes de executar.
- Escala de gravidade: ações de alto risco exigem confirmação humana (human-in-loop).

---

### 7) Observability & Segurança


- Histórico de ações: registar todas as chamadas ao MCP.
- Autenticação: guardar tokens/secrets em secret manager.
- Governance: regras para permitir/recusar ações automáticas, e alertas de escalonamento.

---

### 8) Próximos Passos Práticos (Implementação Incremental)

1. Prova de conceito: rotina local que recebe JSON fixo → chama endpoint MCP mock → executa ciclo uma vez.
2. RAG POC: carregar PDFs em pgvector, indexar, e testar buscas por sintomas reais.
3. Instanciar agente com LangChain Runnable e testar decisões.

5. Produção: migrar para LangServe + orquestrar com LangGraph.

---

### 9) Referências (Documentação e Tutoriais Úteis)

- [Runnables (LangChain docs)](https://api.python.langchain.com)
- [PGVectorStore (LangChain integration)](https://docs.langchain.com)
- [LangGraph (orquestração de agentes/fluxos stateful)](https://docs.langchain.com)

- [LangServe (deploy de runnables)](https://blog.langchain.dev/langserve/)
- [Tutoriais RAG + pgvector (exemplos práticos)](https://codemancers.com/blog/2023-07-10-rag-pgvector/)

---

### 10) Checklist Rápido

- Criar conta/keys LLM e embeddings.
- Levantar Postgres + pgvector (docker).
- Extrair e chunkar PDFs -> gerar embeddings -> popular PGVector.
- Implementar wrappers HTTP para MCP (diagnose/execute/status).
- Implementar agent_runnable com loop e integração com retriever.

- Escrever políticas de segurança (whitelist de actions, limites).

---

### Hotkeys (Atalhos do Conteúdo)

**L 🧩:** LangChain Basics - Overview e exemplos de integração.

**V 🚀:** LangServe Introduction - Features e casos de uso.
**G 🔍:** LangGraph Fundamentals - Propósito e exemplos.
**P 📊:** Pinecone Vector Store - Papel e exemplos.
**E 🧠:** Embeddings and Chunking - Definição e exemplos práticos.
**R ⚙️:** Runnables Explanation - Customização de runnables.

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.9+
- PostgreSQL (para System Simulator)
- OpenAI API Key (para Agent)

### Instalação

1. **Clone o repositório** (se aplicável)

2. **Instale dependências do System Simulator**:
   ```bash
   cd system_simulator
   pip install -r requirements.txt
   ```

3. **Instale dependências do MCP Server**:
   ```bash
   cd mcp_server
   pip install -r requirements.txt
   ```

4. **Instale dependências do Agent**:
   ```bash
   cd agents
   pip install langchain langchain-openai langgraph sentence-transformers
   ```

5. **Configure variáveis de ambiente**:
   ```bash
   export OPENAI_API_KEY="sua-chave-aqui"
   export CLIENT_ID="1"  # ID do cliente para testar
   ```

### Executar

1. **Inicie o System Simulator**:
   ```bash
   cd system_simulator
   python main.py
   ```
   API estará disponível em `http://localhost:9000`

2. **Inicie o MCP Server** (em outro terminal):
   ```bash
   cd mcp_server
   python main.py
   ```

3. **Execute o Agent** (em outro terminal):
   ```bash
   cd agents
   python agent_langgraph.py
   ```

## 📁 Estrutura do Projeto

```
Frankenstein/
├── mcp_server/              # MCP Server - Adaptador Universal
│   ├── main.py             # Servidor MCP principal
│   ├── tool_loader.py      # Carregador de YAMLs
│   ├── tool_registry.py    # Registro de ferramentas
│   ├── openapi.yaml        # Especificação da API
│   └── examples/            # Exemplos de YAMLs
│
├── agents/                  # Agent Cognitivo
│   ├── agent.py            # Agent básico (legado)
│   ├── agent_langgraph.py  # Agent com LangGraph
│   └── rag_procedures.json # Base de conhecimento
│
├── system_simulator/        # Simulador de Sistemas
│   ├── main.py             # API FastAPI
│   ├── api/                # Endpoints
│   ├── models/             # Modelos de dados
│   └── tools/              # YAMLs de ferramentas
│
├── docs/                   # Documentação
│   ├── GUIA_CRIAR_YAML.md  # Como criar novos YAMLs
│   └── ESTRUTURA_SOLUCAO.md # Arquitetura completa
│
└── tests/                  # Testes
    └── test_mcp_loader.py  # Testes do carregador
```

## 🔧 Como Funciona

### 1. Carregamento Dinâmico de Ferramentas

O MCP Server carrega automaticamente ferramentas de arquivos YAML:

- **OpenAPI/Swagger**: Especificações de APIs REST
- **Formato Customizado**: YAMLs com estrutura `tools:`

Basta adicionar um novo arquivo YAML no diretório correto e reiniciar o servidor!

### 2. Diagnóstico Autônomo

O Agent:
1. Consulta sistemas do cliente via MCP
2. Identifica problemas (sistemas inativos, erros)
3. Consulta RAG para procedimentos de resolução
4. Executa ações corretivas via MCP
5. Verifica se problemas foram resolvidos

### 3. Adicionar Novas Ferramentas

Veja o guia completo: [docs/GUIA_CRIAR_YAML.md](docs/GUIA_CRIAR_YAML.md)

**Exemplo rápido - Adicionar API de Notificações:**

```yaml
# system_simulator/tools/notifications.yaml
openapi: 3.0.0
info:
  title: API de Notificações
paths:
  /api/v1/notifications:
    post:
      operationId: send_notification
      summary: Envia uma notificação
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                recipient:
                  type: string
                message:
                  type: string
```

Após reiniciar o MCP Server, a ferramenta `send_notification` estará disponível!

## 📚 Documentação

- [Guia: Como Criar YAMLs](docs/GUIA_CRIAR_YAML.md)
- [Estrutura da Solução](docs/ESTRUTURA_SOLUCAO.md)
- [README do MCP Server](mcp_server/README.md)

## 🧪 Testes

Execute os testes do carregador de ferramentas:

```bash
cd tests
python test_mcp_loader.py
```

## 🔄 Fluxo de Trabalho

### Para Adicionar Nova Ferramenta (Colega)

1. Criar YAML seguindo formato OpenAPI ou customizado
2. Colocar em `system_simulator/tools/` ou `mcp_server/`
3. Testar manualmente a API/função
4. Documentar com exemplos
5. Commit e push

### Para Desenvolver MCP/Agent (Tu)

1. Melhorar `tool_loader.py` ou `tool_registry.py`
2. Integrar com LangGraph
3. Adicionar testes
4. Documentar mudanças

## 🎯 Próximos Passos

- [ ] Integração completa LangGraph + MCP
- [ ] Melhorar RAG com embeddings
- [ ] Suporte para funções Python locais
- [ ] Interface web para gerenciar ferramentas
- [ ] Validação automática de YAMLs

## 📝 Licença

[Adicionar licença aqui]

## 👥 Contribuidores

- [Adicionar nomes]

