from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """проверка работоспособности"""

    return {"status": "ok"}


@router.get("/health/liveness")
async def liveness_probe():
    """проверка жизнеспособности"""

    return {"status": "alive"}


@router.get("/health/startup")
async def startup_probe(request: Request):
    """проверка завершения старта"""

    started = getattr(request.app.state, "startup_complete", False)
    if not started:
        raise HTTPException(status_code=503, detail="application is starting")

    return {"status": "started"}


@router.get("/health/readiness")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """проверка базы данных"""

    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database is not ready") from exc

    return {"status": "ready"}
