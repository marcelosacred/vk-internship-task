from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.startup_complete = True
    yield
    app.state.startup_complete = False


app = FastAPI(
    title="Bot Farm API",
    description="VK Internship Task",
    lifespan=lifespan,

)
app.state.startup_complete = False

app.include_router(health_router)
app.include_router(router, prefix="/api/v1")
