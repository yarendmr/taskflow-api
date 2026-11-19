
from fastapi import FastAPI

from app.api.v1.routers import system
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(system.router)
