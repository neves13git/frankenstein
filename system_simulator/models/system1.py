from sqlalchemy import Column, Integer, String, Boolean
from core.database import Base


class System1(Base):
    __tablename__ = "system1"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, index=True)
    typification = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    error_message = Column(String, default="")
