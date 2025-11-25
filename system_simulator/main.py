# Importe o engine e Base do seu módulo de banco de dados
from core.database import engine, Base # Adapte esta linha conforme seu path real
import uvicorn
from fastapi import FastAPI
from api.v1.endpoints import health, system1, users
import contextlib

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [Startup] A inicializar a base de dados...")
    
    try:
        # AQUI É ONDE VOCÊ CRIA AS TABELAS
        Base.metadata.create_all(bind=engine)
        print("✅ [Startup] Esquema de base de dados criado/verificado com sucesso.")
    except Exception as e:
        print(f"❌ [Startup] ERRO na inicialização/criação de tabelas: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️  [Startup] Servidor iniciando mesmo com erro (endpoints podem falhar)")

    yield
    print("🛑 [Shutdown] Aplicação encerrada.")


app = FastAPI(
        title="System Simulator",
        lifespan=lifespan
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(system1.router, prefix="/api/v1", tags=["System1"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000
    )