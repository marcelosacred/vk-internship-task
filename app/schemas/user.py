from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

# схемы для создания и ответа
# логин это email (!)

class UserCreate(BaseModel):
    login: EmailStr
    password: str
    project_id: UUID
    env: str
    domain: str


class UserResponse(BaseModel):
    id: UUID
    created_at: datetime
    login: str
    project_id: UUID
    env: str
    domain: str
    locktime: Optional[datetime] = None

    class Config:
        from_attributes = True
