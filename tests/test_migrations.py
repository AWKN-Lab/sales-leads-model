"""迁移验收（工单验收第 1、2 条）：upgrade head / downgrade -1 / alembic check。"""
import pytest
import io
import re

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    return cfg


def test_upgrade_head_creates_tables_and_indexes(database_url):
    """空库上 alembic upgrade head 成功，且表/索引齐全。"""
    cfg = _cfg()
    command.upgrade(cfg, "head")
    eng = create_engine(database_url)
    insp = inspect(eng)
    tables = set(insp.get_table_names())
    assert {"sales_leads", "sales_lead_owner_logs"} <= tables
    idx = {i["name"] for i in insp.get_indexes("sales_leads")}
    assert {
        "uq_sales_leads_org_uscc",
        "ix_sales_leads_org_company_norm",
        "ix_sales_leads_org_mobile_hash",
        "ix_sales_leads_org_site_owner_stage",
    } <= idx
    # 部分唯一索引必须是「条件索引」且 unique
    uq = [i for i in insp.get_indexes("sales_leads") if i["name"] == "uq_sales_leads_org_uscc"][0]
    assert uq["unique"] is True
    db_where = str(uq.get("dialect_options", {}).get("postgresql_where"))
    assert "uscc IS NOT NULL" in db_where and "deleted_at IS NULL" in db_where
    eng.dispose()


def _norm_where(text: str) -> str:
    """归一化 WHERE 片段（PG 回读会加括号，比较前先去掉空白与括号）。"""
    return re.sub(r"[\s()]+", "", text or "").lower()


def test_model_and_database_agree_on_partial_index_condition(database_url):
    """模型里的部分唯一索引条件必须与库里的**一致**。

    为什么单独写这条：`alembic check` **不比较索引的部分索引条件（postgresql_where）**，
    模型漂移了它也不会报 ⇒ 必须自己断言，否则「模型与库不一致」会一直潜伏。
    """
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex

    from app.models import SalesLead

    cfg = _cfg()
    command.upgrade(cfg, "head")        # 先确保 schema 是最新的（这条用例要能单独跑）
    eng = create_engine(database_url)
    insp = inspect(eng)
    db_idx = [i for i in insp.get_indexes("sales_leads") if i["name"] == "uq_sales_leads_org_uscc"][0]
    db_where = str(db_idx.get("dialect_options", {}).get("postgresql_where"))

    # SQLAlchemy 2.1 的 table.indexes 是**集合**，不是按名索引的字典
    model_idx = next(i for i in SalesLead.__table__.indexes if i.name == "uq_sales_leads_org_uscc")
    model_ddl = str(CreateIndex(model_idx).compile(dialect=postgresql.dialect()))
    m = re.search(r"WHERE (.+?)$", model_ddl, re.S | re.I)
    model_where = m.group(1) if m else ""

    assert _norm_where(db_where) == _norm_where(model_where), (
        f"模型与库的部分索引条件不一致：模型={model_where!r} 库={db_where!r}"
    )
    assert "usccisnotnull" in _norm_where(db_where)
    assert "deleted_atisnull" in _norm_where(db_where)
    eng.dispose()


def test_alembic_check_reports_no_new_operations(database_url):
    """验收第 2 条：alembic check 输出 No new upgrade operations detected。"""
    cfg = _cfg()
    command.upgrade(cfg, "head")
    # alembic 的 check 结论走 config.print_stdout ⇒ 显式接管 stdout，不依赖 pytest 捕获时机
    buf = io.StringIO()
    cfg.stdout = buf
    command.check(cfg)      # 有差异会抛异常
    out = buf.getvalue()
    assert "No new upgrade operations detected" in out, out


def test_downgrade_one_removes_tables_then_restores(database_url):
    """验收第 1 条：alembic downgrade -1 成功（表被清理），随后 upgrade head 可复原。"""
    cfg = _cfg()
    command.upgrade(cfg, "head")
    eng = create_engine(database_url)
    command.downgrade(cfg, "-1")
    insp = inspect(eng)
    assert "sales_leads" not in insp.get_table_names()
    assert "sales_lead_owner_logs" not in insp.get_table_names()
    # 复原，保证后续用例仍处于 head 状态
    command.upgrade(cfg, "head")
    assert "sales_leads" in inspect(eng).get_table_names()
    eng.dispose()
