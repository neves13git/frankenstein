# nodes/verification_node.py

from typing import Dict

async def verification_node(state: Dict) -> Dict:
    """
    Verifica se os problemas foram resolvidos.
    """
    print("\n" + "="*60)
    print("✔️  [VERIFICATION NODE] Verificando correções...")
    print("="*60)
    
    correction_result = state.get("correction_result", {})
    problems = state.get("problems", [])
    max_attempts = state.get("max_attempts", 3)
    current_attempts = state.get("correction_attempts", 0)
    
    if not correction_result:
        print("⚠️  Nenhuma correção foi executada!")
        return {
            "verification_result": {"resolved": False},
            "escalated": False
        }
    
    # Verificar quais problemas foram resolvidos
    resolved_count = sum(1 for r in correction_result.values() if r.get("success"))
    total_problems = len(problems)
    
    print(f"\n📊 Resultado:")
    print(f"   ✅ Resolvidos: {resolved_count}/{total_problems}")
    print(f"   🔄 Tentativas: {current_attempts}/{max_attempts}")
    
    # Decidir se precisa escalar
    escalated = False
    
    if resolved_count < total_problems and current_attempts >= max_attempts:
        print(f"\n⚠️  Limite de tentativas atingido! Escalando para humano...")
        escalated = True
    elif resolved_count == total_problems:
        print(f"\n🎉 Todos os problemas foram resolvidos!")
    
    return {
        "verification_result": {
            "resolved": resolved_count == total_problems,
            "resolved_count": resolved_count,
            "total_problems": total_problems
        },
        "escalated": escalated
    }