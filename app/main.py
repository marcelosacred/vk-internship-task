from fastapi import FastAPI

from app.api.routes import router
from app.db.database import init_db

app = FastAPI(title="Bot Farm API", description="VK Internship Task")

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get("/health")
async def health_check():
    """проверка работоспособности сервиса"""
    return {"status": "ok"}
