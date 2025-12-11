# nodes/human_escalation.py

from typing import Dict

async def human_escalation_node(state: Dict) -> Dict:
    """
    Escala problemas não resolvidos para um humano.
    """
    print("\n" + "="*60)
    print("👤 [HUMAN ESCALATION] Escalando para suporte humano...")
    print("="*60)
    
    problems = state.get("problems", [])
    correction_result = state.get("correction_result", {})
    
    # Identificar problemas não resolvidos
    unresolved = []
    for problem in problems:
        problem_id = problem["id"]
        if problem_id not in correction_result or not correction_result[problem_id].get("success"):
            unresolved.append(problem)
    
    print(f"\n📋 Problemas não resolvidos: {len(unresolved)}")
    for prob in unresolved:
        print(f"   ❌ {prob['description']}")
    
    print(f"\n📧 Ticket criado para suporte humano!")
    print(f"   Client ID: {state['client_id']}")
    print(f"   Tentativas: {state.get('correction_attempts', 0)}")
    
    return {
        "escalated": True
    }