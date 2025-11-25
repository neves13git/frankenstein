from fastapi import APIRouter

router = APIRouter()

@router.get("/health", status_code=200)
def health_check():
    """Verifica o estado da API."""
    return {"status": "ok", "service": "FastAPI", "version": "v1"}