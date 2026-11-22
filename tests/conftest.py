"""测试夹具：用 pgserver 起一个**真实的 PostgreSQL 16**（不是 mock）。"""
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def pg_url(tmp_path_factory):
    """起一个临时 PG16 实例，返回连接串。"""
    import pgserver

    pgdata = tmp_path_factory.mktemp("pgdata")
    db = pgserver.get_server(str(pgdata))
    uri = db.get_uri()
    yield uri
    db.cleanup()


@pytest.fixture(scope="session")
def database_url(pg_url):
    os.environ["DATABASE_URL"] = pg_url
    return pg_url


@pytest.fixture()
def engine(database_url):
    from app.db import build_engine

    eng = build_engine(database_url)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def _clean_db(request):
    """每个用例前清空业务表（会话级 PG 实例被多个用例共用 ⇒ 必须隔离数据）。"""
    if "database_url" not in request.fixturenames:
        yield
        return
    from sqlalchemy import text as sql_text

    from app.db import build_engine

    url = request.getfixturevalue("database_url")
    eng = build_engine(url)
    with eng.begin() as conn:
        exists = conn.execute(sql_text("SELECT to_regclass('public.sales_leads')")).scalar()
        if exists:
            conn.execute(sql_text("TRUNCATE sales_leads, sales_lead_owner_logs CASCADE"))
    eng.dispose()
    yield
