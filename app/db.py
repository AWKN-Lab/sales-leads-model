"""数据库连接（SQLAlchemy 2 引擎与会话工厂）。"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "DATABASE_URL"


def database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        raise RuntimeError(f"缺少环境变量 {DATABASE_URL_ENV}（连接串只从环境变量读取）")
    return url


def build_engine(url: str | None = None):
    return create_engine(url or database_url(), future=True, pool_pre_ping=True)


def build_session_factory(engine=None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or build_engine(), expire_on_commit=False, future=True)
