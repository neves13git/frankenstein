# nodes/analysis_node.py

import os
import json
import openai
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def analysis_node(state: Dict) -> Dict:
    """
    Analisa o resultado do scan usando LLM para identificar problemas de forma dinâmica.
    O LLM deve analisar QUALQUER estrutura de dados e identificar problemas reais.
    """
    print("\n" + "="*60)
    print("🔬 [ANALYSIS NODE] Analisando resultados...")
    print("="*60)
    
    scan_result = state.get("scan_result")
    
    if not scan_result:
        print("⚠️  No scan results available!")
        state["problems"] = []
        return state
    
    # Extrair o texto do resultado do MCP
    result_data = scan_result.get("result", [])
    if result_data and isinstance(result_data, list) and len(result_data) > 0:
        text_content = result_data[0].get("text", "")
        print(f"📄 Data received from scan:")
        print(f"{text_content}")
        print()
    else:
        print("⚠️  Unexpected result format!")
        state["problems"] = []
        return state
    
    # Parse do JSON para validar
    try:
        systems_data = json.loads(text_content)
        print(f"✅ JSON parseado com sucesso: {len(systems_data)} sistemas encontrados")
    except json.JSONDecodeError as e:
        print(f"⚠️  Erro ao fazer parse do JSON: {e}")
        state["problems"] = []
        return state
    
    # Preparar prompt GENÉRICO - sem assumir estrutura específica
    prompt = f"""You are a system analyzer that identifies REAL PROBLEMS in structured data.

RECEIVED DATA:
```json
{json.dumps(systems_data, indent=2)}
```

CRITICAL RULES FOR PROBLEM IDENTIFICATION:

1. ✅ **THESE ARE PROBLEMS** (must be reported):
   - is_active = false (system is inactive/disabled)
   - is_active = false AND error_message has content (critical - failed system)
   - is_active = true AND error_message has content (medium - system with error)

2. ❌ **THESE ARE NOT PROBLEMS** (DO NOT REPORT):
   - is_active = true AND error_message = "" (empty string)
   - is_active = true AND error_message is null or missing
   - Any system that is active WITHOUT errors
   - Empty error_message means "NO ERROR" - this is NORMAL

3. **SEVERITY CLASSIFICATION:**
   - CRITICAL: is_active=false AND error_message filled
   - HIGH: is_active=false AND error_message empty (provisioning issue)
   - MEDIUM: is_active=true AND error_message filled
   - DO NOT use "low" severity - if it's low, it's not a problem

4. **OUTPUT FORMAT:**
For each REAL problem found, return:
{{
  "id": "problem_<system_id>",
  "type": "inactive_with_error" | "inactive_no_error" | "active_with_error",
  "system_id": <id>,
  "severity": "critical" | "high" | "medium",
  "description": "Clear problem description based on system state",
  "details": <complete system object>
}}

**IMPORTANT**: 
- If ALL systems have is_active=true and error_message="" → Return EMPTY array: []
- Empty error_message is NORMAL, not a problem
- Only report ACTUAL problems, not normal states

RETURN ONLY THE JSON ARRAY, NO MARKDOWN OR EXPLANATIONS:"""

    print(f"\n🤖 Sending data to LLM for analysis...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai.api_key)
        
        system_content = """You are a system analyzer that:
1. ONLY identifies REAL problems (inactive systems or systems with errors)
2. DOES NOT report systems that are working normally (active + no errors)
3. Returns ONLY valid JSON arrays without markdown
4. Returns empty array [] when NO problems exist
5. Understands that empty error_message means NO ERROR (normal state)
6. Uses logical reasoning: active=true + error_message="" = WORKING CORRECTLY = NOT A PROBLEM"""
        
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        print(f"📥 Response received from LLM:")
        print(f"{analysis_result[:500]}...")
        print()
        
        # Limpar markdown se existir
        if "```" in analysis_result:
            parts = analysis_result.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("[") or part.startswith("{"):
                    analysis_result = part
                    break
        
        # Parse do JSON
        problems = json.loads(analysis_result)
        
        # Validar que é uma lista
        if not isinstance(problems, list):
            print(f"⚠️  LLM did not return a list. Type received: {type(problems)}")
            problems = []
        
        # Validação adicional: LLM pode ajudar a confirmar se o problema é real
        # em vez de hardcoded logic
        validated_problems = []
        for prob in problems:
            details = prob.get("details", {})
            
            # Verificação genérica: se LLM identificou, confiamos mas fazemos sanity check
            # Se details está vazio ou None, provavelmente é falso positivo
            if details and isinstance(details, dict) and len(details) > 0:
                validated_problems.append(prob)
                print(f"✅ Problem validated: {prob.get('description', 'No description')}")
            else:
                print(f"⚠️  Problem without details ignored: {prob.get('id', 'unknown')}")
        
        problems = validated_problems
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing LLM response: {e}")
        print(f"Response received: {analysis_result}")
        problems = []
    except Exception as e:
        print(f"❌ Error querying LLM: {e}")
        import traceback
        traceback.print_exc()
        problems = []
    
    print(f"\n📋 Problems found after validation: {len(problems)}")
    if problems:
        for prob in problems:
            severity = prob.get('severity', 'unknown')
            description = prob.get('description', 'Unknown')
            print(f"   ❌ [{severity}] {description}")
    else:
        print("✅ No problems found! All systems are working correctly.")
    
    state["problems"] = problems
    return state