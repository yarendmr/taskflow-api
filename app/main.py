
from fastapi import FastAPI

from app.api.v1.routers import admin, auth, system, users
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(system.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)