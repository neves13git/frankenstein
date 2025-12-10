# nodes/rag_search_node.py

import os
import json
import openai
from typing import Dict
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def rag_search_node(state: Dict) -> Dict:
    """
    Uses RAG (Qdrant) + LLM to search for solutions in knowledge base
    and determine which MCP tool to use to resolve each problem.
    """
    print("\n" + "="*60)
    print("📚 [RAG SEARCH NODE] Searching for solutions in RAG...")
    print("="*60)
    
    problems = state.get("problems", [])
    tools = state.get("tools", [])
    qdrant_client = state.get("vector_store")
    
    if not problems:
        print("✅ No problems to search for solutions!")
        state["rag_info"] = None
        return state
    
    # Preparar informação das ferramentas disponíveis
    tools_description = "\n".join([
        f"- {t['name']}: {t.get('description', '')}\n  Input: {json.dumps(t.get('inputSchema', {}), indent=2)}"
        for t in tools
    ])
    
    rag_info = {}
    
    for problem in problems:
        print(f"\n🔍 Analyzing: {problem.get('description', 'No description')}")
        
        # 1. Buscar no RAG documentos relevantes
        rag_context = ""
        rag_found = False
        if qdrant_client:
            try:
                print(f"   📖 Searching in knowledge base...")
                
                # Gerar embedding da query - MELHORAR A QUERY COM MAIS CONTEXTO
                from openai import OpenAI
                openai_client = OpenAI(api_key=openai.api_key)
                
                # Extrair detalhes do problema para criar query mais rica
                details = problem.get('details', {})
                typification = details.get('typification', '')
                is_active = details.get('is_active', True)
                error_message = details.get('error_message', '')
                
                # Construir query FOCADA EM SINTOMAS ESPECÍFICOS
                query_parts = []
                
                # PRIORIDADE 1: Error message (sintoma mais específico)
                if error_message and error_message.strip():
                    # Extrair palavras-chave do erro
                    error_lower = error_message.lower()
                    
                    # Mapear erros para sintomas
                    if "offline" in error_lower or "disconnected" in error_lower:
                        query_parts.append("equipamento offline hardware desconectado problema físico")
                    elif "timeout" in error_lower or "no response" in error_lower:
                        query_parts.append("connection timeout erro de conectividade")
                    elif "auth" in error_lower or "authentication" in error_lower:
                        query_parts.append("authentication failed erro de autenticação credenciais")
                    else:
                        # Erro genérico - incluir texto literal
                        query_parts.append(f"erro {error_message}")
                    
                    # Se inativo COM erro, é diferente de inativo SEM erro
                    if not is_active:
                        query_parts.append("sistema inativo com erro")
                    else:
                        query_parts.append("sistema ativo com erro")
                
                # PRIORIDADE 2: Estado sem erro (provisionamento)
                elif not is_active:
                    # Inativo SEM error_message = problema de provisionamento
                    query_parts.append("sistema inativo sem erro provisionamento ativação")
                    if typification:
                        query_parts.append(f"{typification}")
                
                # PRIORIDADE 3: Descrição do problema (pode conter sintomas do cliente)
                description = problem.get('description', '')
                if description:
                    # Detectar sintomas físicos na descrição
                    desc_lower = description.lower()
                    if any(word in desc_lower for word in ["luz", "led", "apagada", "vermelha"]):
                        query_parts.append("luz apagada LED problema físico router")
                    elif any(word in desc_lower for word in ["desligado", "sem energia", "não liga"]):
                        query_parts.append("router desligado sem energia problema físico")
                    else:
                        query_parts.append(description)
                
                # Adicionar tipo de problema
                problem_type = problem.get('type', '')
                if problem_type:
                    query_parts.append(problem_type)
                
                query = " ".join(query_parts)
                print(f"   🔎 Symptom-focused search query: '{query}'")
                
                embedding_response = openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query
                )
                query_embedding = embedding_response.data[0].embedding
                
                # Buscar no Qdrant com mais resultados
                search_results = qdrant_client.query_points(
                    collection_name="technical_solutions",
                    query=query_embedding,
                    limit=5  # Aumentar para 5 resultados
                )
                
                # Extrair pontos
                points = search_results[0] if isinstance(search_results, tuple) else search_results.points
                
                # Mostrar todos os scores para debug
                if points:
                    print(f"   📊 Scores found:")
                    for i, point in enumerate(points, 1):
                        print(f"      {i}. Score: {point.score:.4f}")
                
                # Verificar se há documentos com score mínimo aceitável (threshold)
                min_score = 0.5  # REDUZIR threshold de 0.7 para 0.5
                relevant_points = [p for p in points if p.score >= min_score]
                
                if relevant_points:
                    rag_found = True
                    print(f"   ✅ Found {len(relevant_points)} relevant documents")
                    rag_context = "\n\nDocumentos relevantes do knowledge base:\n"
                    for i, point in enumerate(relevant_points, 1):
                        rag_context += f"\n[Documento {i}] (Score: {point.score:.3f})\n{point.payload['text']}\n"
                else:
                    print(f"   ⚠️  No relevant documents found (score < {min_score})")
            except Exception as e:
                print(f"   ⚠️  Error searching in Qdrant: {e}")
        else:
            print(f"   ⚠️  Qdrant not available")
        
        # Se não encontrou documentos relevantes na RAG, não tentar resolver
        if not rag_found:
            print(f"   ❌ No known procedures for this problem - Will be escalated")
            rag_info[problem["id"]] = {
                "recommended_tool": None,
                "tool_args": {},
                "reasoning": "No procedure found in knowledge base. Escalate to human."
            }
            continue
        
        # 2. Prepare prompt for LLM to decide tool and arguments
        prompt = f"""
You have the following problem in a system:
{json.dumps(problem, indent=2)}
{rag_context}

Available MCP Tools:
{tools_description}

CRITICAL ANALYSIS RULES:

1. **ALWAYS analyze error_message FIRST**
   - If contains "offline", "hardware", "disconnected", "equipment" → ESCALATE (return null)
   - If contains "timeout", "authentication" → Can try update_system_by_id
   - If empty and is_active=false → Use update_system_by_id to activate

2. **PHYSICAL SYMPTOMS = ESCALATE**
   - Description mentions "luz apagada", "LED", "router desligado" → ESCALATE (return null)
   - Hardware problems CANNOT be resolved via API

3. **Only recommend tool if:**
   - Documentation EXPLICITLY describes solution
   - Problem is LOGICAL (not physical)
   - There is clear documented procedure

4. **If documentation says "ESCALAR" or "ESCALATE" → return null**

5. **TOOL SELECTION GUIDE:**
   - To activate inactive system → "update_system_by_id"
   - To clear error message → "update_system_by_id"
   - To get system details → "get_system_by_id"
   - If must escalate → null

6. **DO NOT invent solutions**
   - If in doubt → null (escalate)
   - If no clear documentation → null (escalate)

Analyze the problem and documentation carefully:
1. Does documentation recommend ESCALATE? → Return null
2. Does documentation provide API solution? → Return exact tool name
3. Can you determine the correct arguments from the problem details?

**EXAMPLES OF CORRECT RESPONSES:**

Example 1 - Connection Timeout (CAN FIX):
{{
  "recommended_tool": "update_system_by_id",
  "tool_args": {{"system_id": 1, "body": {{"is_active": true, "error_message": ""}}}},
  "reasoning": "Documentation states Connection Timeout can be resolved by reactivating system and clearing error using update_system_by_id"
}}

Example 2 - Equipment Offline (MUST ESCALATE):
{{
  "recommended_tool": null,
  "tool_args": {{}},
  "reasoning": "Documentation states 'Equipment Offline' indicates physical problem requiring technician escalation"
}}

Example 3 - Inactive without error (CAN FIX):
{{
  "recommended_tool": "update_system_by_id",
  "tool_args": {{"system_id": 1, "body": {{"is_active": true}}}},
  "reasoning": "Documentation states inactive system without error is provisioning issue resolved by activating via update_system_by_id"
}}

Respond ONLY with valid JSON following this exact format.
"""

        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert technical support analyst. Your job is to match problems to documented solutions. When documentation provides a clear API-based solution, return the EXACT tool name. When documentation says ESCALATE or problem is physical, return null. You must follow documented procedures exactly - never improvise."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0
            )
            solution_text = response.choices[0].message.content.strip()
            
            # Parse do JSON
            if solution_text.startswith("```"):
                solution_text = solution_text.split("```")[1]
                if solution_text.startswith("json"):
                    solution_text = solution_text[4:]
                solution_text = solution_text.strip()
            
            solution = json.loads(solution_text)
            
            # Validar se o LLM retornou uma solução válida
            if solution.get("recommended_tool") is None or solution.get("recommended_tool") == "null":
                print(f"   ❌ LLM did not find documented solution - Will be escalated")
                rag_info[problem["id"]] = {
                    "recommended_tool": None,
                    "tool_args": {},
                    "reasoning": solution.get("reasoning", "No documented procedure")
                }
            else:
                rag_info[problem["id"]] = solution
                print(f"   ✅ Solution: Use '{solution['recommended_tool']}'")
                print(f"   📝 Reasoning: {solution.get('reasoning', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error determining solution: {e}")
            rag_info[problem["id"]] = {
                "recommended_tool": None,
                "tool_args": {},
                "reasoning": f"Error: {e}"
            }
    
    state["rag_info"] = rag_info
    return state