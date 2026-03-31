import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    login = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    env = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    locktime = Column(DateTime, nullable=True)
