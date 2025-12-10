"""
workflow.py - Define o workflow do agente LLM
"""

from typing import TypedDict, Optional, Literal
import os
from mcp_client import MCPClient
from nodes.scan_node import scan_node
from nodes.analysis_node import analysis_node
from nodes.rag_search_node import rag_search_node
from nodes.correction_node import correction_node
from nodes.human_escalation import human_escalation_node
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

# Estado tipado
class AgentState(TypedDict, total=False):
    client_id: int
    mcp_client: MCPClient
    vector_store: Optional[object]  # Qdrant vector store
    tools: Optional[list]
    scan_result: Optional[dict]
    problems: Optional[list]
    rag_info: Optional[dict]
    correction_result: Optional[dict]
    verification_result: Optional[dict]
    escalated: bool

def get_initial_state() -> AgentState:
    """
    Inicializa o estado do agente incluindo conexão ao Qdrant.
    """
    print("\n🔧 Initializing agent state...")
    
    # Conectar ao Qdrant
    vector_store = None
    try:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_client = QdrantClient(url=qdrant_url)
        
        # Testar conexão
        collections = qdrant_client.get_collections()
        vector_store = qdrant_client
        print(f"✅ Connected to Qdrant at {qdrant_url}")
        
    except Exception as e:
        print(f"⚠️  Error connecting to Qdrant: {e}")
        print("⚠️  Continuing without RAG (some features limited)")
        print("💡 Start Qdrant: docker-compose up -d")
    
    return AgentState(
        client_id=1,
        mcp_client=MCPClient(),
        vector_store=vector_store,
        tools=None,
        scan_result=None,
        problems=None,
        rag_info=None,
        correction_result=None,
        verification_result=None,
        escalated=False
    )

async def run_agent_workflow():
    # Nodes wrappers
    async def scan_node_wrap(state: AgentState):
        return await scan_node(state)
    async def analysis_node_wrap(state: AgentState):
        return await analysis_node(state)
    async def rag_search_node_wrap(state: AgentState):
        return await rag_search_node(state)
    async def correction_node_wrap(state: AgentState):
        return await correction_node(state)
    async def human_escalation_node_wrap(state: AgentState):
        return await human_escalation_node(state)

    # Cria o grafo de estados
    workflow = StateGraph(AgentState)
    
    # Adicionar nodes
    workflow.add_node("scan", scan_node_wrap)
    workflow.add_node("analysis", analysis_node_wrap)
    workflow.add_node("rag_search", rag_search_node_wrap)
    workflow.add_node("correction", correction_node_wrap)
    workflow.add_node("escalation", human_escalation_node_wrap)

    # Define as transições
    workflow.add_edge("scan", "analysis")
    
    # Decisão após análise: se houver problemas, vai para RAG; senão termina
    def  analysis_decision(state: AgentState) -> Literal["rag_search", "end"]:
        """
        Decide se há problemas para resolver ou se termina.
        """
        problems = state.get("problems", [])
        if problems and len(problems) > 0:
            return "rag_search"  # Há problemas, continuar ciclo
        else:
            print("\n" + "="*60)
            print("✅ NO PROBLEMS FOUND - All systems OK!")
            print("="*60)
            return "end"  # Sem problemas, terminar
    
    workflow.add_conditional_edges(
        "analysis",
        analysis_decision,
        {
            "rag_search": "rag_search",
            "end": END
        }
    )
    
    # Fluxo de correção - sempre volta ao scan para verificar
    workflow.add_edge("rag_search", "correction")
    
    # Após correção, volta SEMPRE ao scan (o scan é que vai verificar se resolveu)
    def correction_decision(state: AgentState) -> Literal["scan", "escalation"]:
        """
        Após correção, decide se volta ao scan ou escala para humano.
        Se RAG não encontrou solução (recommended_tool=None), escala.
        Caso contrário, volta ao scan para verificar se resolveu.
        """
        rag_info = state.get("rag_info", {})
        
        # Verificar se há alguma solução que não foi encontrada (None)
        unsolved_problems = []
        for problem_id, solution in rag_info.items():
            if solution.get("recommended_tool") is None:
                unsolved_problems.append(problem_id)
        
        if unsolved_problems:
            print(f"\n⚠️  {len(unsolved_problems)} problem(s) without documented solution - Escalating...")
            return "escalation"
        
        # Have solutions, were applied, now verify if they worked
        print("\n✅ Corrections applied - Returning to scan to verify...")
        return "scan"
    
    workflow.add_conditional_edges(
        "correction",
        correction_decision,
        {
            "scan": "scan",
            "escalation": "escalation"
        }
    )
    
    # Escalation termina o workflow
    workflow.add_edge("escalation", END)

    # Definir entry point e compilar workflow
    workflow.set_entry_point("scan")
    compiled_workflow = workflow.compile()

    # ✅ CORREÇÃO: Usar ainvoke ao invés de run
    state = get_initial_state()
    final_state = await compiled_workflow.ainvoke(state)
    
    print("[AGENT] Process finished. Final state:")
    print(final_state)
    
    return final_state