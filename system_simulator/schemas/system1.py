from pydantic import BaseModel


class System1Read(BaseModel):
    id: int
    client_id: int
    typification: str
    is_active: bool
    error_message: str

    class Config:
        from_attributes = True

class System1Update(BaseModel):
    typification: str | None = None
    is_active: bool | None = None
    error_message: str | None = None