# agent.py - Apenas executa o workflow do agente
import asyncio
from workflow import run_agent_workflow

if __name__ == "__main__":
    asyncio.run(run_agent_workflow())