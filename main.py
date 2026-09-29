from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import engine
from routers import tasks
import models.tasks

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan started")
    yield
    logger.info("Shutting down server")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "task-api"}


app.include_router(tasks.router)
