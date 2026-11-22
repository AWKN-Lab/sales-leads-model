"""工单验收第 4 条：同一 org 下插入两条相同 uscc 的未删除记录 ⇒ 被数据库拒绝。"""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import build_engine
from app.models import SalesLead

ORG = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
OTHER_ORG = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
USCC = "91310000MA1FL0000X"


def _lead(**kw) -> SalesLead:
    data = dict(
        org_id=ORG,
        site_id=None,
        company_name="某某科技有限公司",
        company_name_norm="某某科技",
        uscc=USCC,
        source_channel="other",
        pool_status="public",
        stage="new",
    )
    data.update(kw)
    return SalesLead(**data)


@pytest.fixture()
def session(database_url):
    eng = build_engine(database_url)
    with Session(eng) as s:
        yield s
    eng.dispose()


def test_duplicate_uscc_in_same_org_is_rejected_by_database(session):
    """同 org、同 uscc、未软删除 ⇒ 第二条被 DB 拒绝（IntegrityError）。"""
    session.add(_lead())
    session.commit()

    with pytest.raises(IntegrityError) as err:
        session.add(_lead(company_name="另一家科技有限公司", company_name_norm="另一家科技"))
        session.commit()
    session.rollback()
    # 必须是**唯一索引**拒绝，而不是应用层
    assert "uq_sales_leads_org_uscc" in str(err.value) or "duplicate key" in str(err.value).lower()


def test_same_uscc_in_different_org_is_allowed(session):
    """不同 org ⇒ 互不冲突（多租户隔离）。"""
    session.add(_lead())
    session.add(_lead(org_id=OTHER_ORG))
    session.commit()
    rows = session.scalars(select(SalesLead)).all()
    assert len(rows) == 2


def test_soft_deleted_row_does_not_block_new_row(session):
    """已软删除的同 uscc 记录不占用唯一键（部分唯一索引的条件）。"""
    lead = _lead()
    session.add(lead)
    session.commit()
    lead.deleted_at = lead.updated_at
    session.commit()

    session.add(_lead(company_name="新公司科技有限公司", company_name_norm="新公司科技"))
    session.commit()
    rows = session.scalars(select(SalesLead)).all()
    assert len(rows) == 2


def test_null_uscc_allows_multiple_rows(session):
    """uscc 可空 ⇒ 多条空 uscc 不冲突。"""
    session.add(_lead(uscc=None))
    session.add(_lead(uscc=None, company_name_norm="另一家"))
    session.commit()
    assert len(session.scalars(select(SalesLead)).all()) == 2
