
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from app.core.config import settings

from typing import Generator

from sqlalchemy.orm import Session, sessionmaker
# PostgreSQL connection URL
database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.db_user,
    password=settings.db_password.get_secret_value(),
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)


# SQLAlchemy engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,
)


# Database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
