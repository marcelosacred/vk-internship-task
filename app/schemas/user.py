from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

# схемы для создания и ответа
# логин это email (!)

class EnvironmentEnum(str, Enum):
    PROD = "prod"
    PREPROD = "preprod"
    STAGE = "stage"


class DomainEnum(str, Enum):
    CANARY = "canary"
    REGULAR = "regular"


class UserCreate(BaseModel):
    login: EmailStr
    password: str
    project_id: UUID
    env: EnvironmentEnum
    domain: DomainEnum


class UserResponse(BaseModel):
    id: UUID
    created_at: datetime
    login: str
    project_id: UUID
    env: EnvironmentEnum
    domain: DomainEnum
    locktime: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
