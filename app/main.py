from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.database import init_db



@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Bot Farm API",
    description="VK Internship Task",
    lifespan=lifespan,

)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """проверка работоспособности сервиса"""
    return {"status": "ok"}
