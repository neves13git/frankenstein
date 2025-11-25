from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def get_users():
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Carol"}
    ]
