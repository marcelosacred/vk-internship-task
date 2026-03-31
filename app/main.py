from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Bot Farm API", description="VK Internship Task")

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """проверка работоспособности сервиса"""
    return {"status": "ok"}
