from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import api
from app.session import start_cleanup, stop_cleanup


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_cleanup()
    yield
    stop_cleanup()


app = FastAPI(title="CV Optim Agent", version="0.1.0", lifespan=lifespan)

app.include_router(api.router, prefix="/api")

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
