"""真实 PostgreSQL：组织关联、公海归属、报备时间的回归门禁。"""
import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session

from app.models import SalesLead, SalesLeadOwnerLog

ORG = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
OTHER = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
OWNER = uuid.UUID("00000000-0000-0000-0000-000000000011")
FORGED = datetime(2000, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def ready(engine, database_url):
    command.upgrade(Config("alembic.ini"), "head")
    return engine


def lead(**kw):
    data = dict(id=uuid.uuid4(), org_id=ORG, company_name="虚构测试公司",
                company_name_norm="虚构测试", source_channel="other")
    data.update(kw)
    return data


def test_cross_org_log_database_rejected(ready):
    row = lead()
    with ready.begin() as conn:
        conn.execute(SalesLead.__table__.insert().values(**row))
    with pytest.raises(IntegrityError, match="fk_sales_lead_owner_logs_org_lead"):
        with ready.begin() as conn:
            conn.execute(SalesLeadOwnerLog.__table__.insert().values(
                org_id=OTHER, lead_id=row["id"], action="register"))


def test_same_org_log_allowed_and_cross_org_reparent_rejected(ready):
    row = lead()
    with ready.begin() as conn:
        conn.execute(SalesLead.__table__.insert().values(**row))
        log_id = conn.execute(SalesLeadOwnerLog.__table__.insert().values(
            org_id=ORG, lead_id=row["id"], action="register").returning(SalesLeadOwnerLog.id)).scalar_one()
    with pytest.raises(IntegrityError, match="fk_sales_lead_owner_logs_org_lead"):
        with ready.begin() as conn:
            conn.execute(SalesLeadOwnerLog.__table__.update().where(
                SalesLeadOwnerLog.id == log_id).values(org_id=OTHER))


@pytest.mark.parametrize("pool,owner", [("public", OWNER), ("owned", None)])
def test_invalid_pool_owner_rejected(ready, pool, owner):
    with pytest.raises(IntegrityError, match="ck_sales_leads_pool_owner"):
        with ready.begin() as conn:
            conn.execute(SalesLead.__table__.insert().values(**lead(pool_status=pool, owner_id=owner)))


def test_valid_pool_transition_and_invalid_update(ready):
    row = lead(pool_status="public", owner_id=None)
    with ready.begin() as conn:
        conn.execute(SalesLead.__table__.insert().values(**row))
        conn.execute(SalesLead.__table__.update().where(SalesLead.id == row["id"]).values(
            pool_status="owned", owner_id=OWNER))
    with pytest.raises(IntegrityError, match="ck_sales_leads_pool_owner"):
        with ready.begin() as conn:
            conn.execute(SalesLead.__table__.update().where(SalesLead.id == row["id"]).values(pool_status="public"))
    with ready.begin() as conn:
        conn.execute(SalesLead.__table__.update().where(SalesLead.id == row["id"]).values(
            pool_status="public", owner_id=None))


@pytest.mark.parametrize("explicit", [False, True])
def test_registered_at_server_assigned_on_insert(ready, explicit):
    row = lead()
    if explicit:
        row["registered_at"] = FORGED
    with ready.begin() as conn:
        before = conn.scalar(text("SELECT clock_timestamp()"))
        value = conn.execute(SalesLead.__table__.insert().values(**row).returning(
            SalesLead.registered_at)).scalar_one()
        after = conn.scalar(text("SELECT clock_timestamp()"))
        assert before <= value <= after


def test_registered_at_immutable_and_other_updates_allowed(ready):
    row = lead()
    with ready.begin() as conn:
        original = conn.execute(SalesLead.__table__.insert().values(**row).returning(
            SalesLead.registered_at)).scalar_one()
    with pytest.raises(DBAPIError, match="registered_at is immutable") as err:
        with ready.begin() as conn:
            conn.execute(SalesLead.__table__.update().where(SalesLead.id == row["id"]).values(
                registered_at=FORGED))
    assert getattr(err.value.orig, "sqlstate", None) == "23514"
    with ready.begin() as conn:
        conn.execute(SalesLead.__table__.update().where(SalesLead.id == row["id"]).values(stage="contacted"))
        current = conn.execute(select(SalesLead.registered_at, SalesLead.stage).where(
            SalesLead.id == row["id"])).one()
        assert current == (original, "contacted")


def test_orm_relationship_and_server_timestamp(ready):
    with Session(ready) as session:
        row = SalesLead(**lead(registered_at=FORGED))
        row.logs.append(SalesLeadOwnerLog(org_id=ORG, action="register"))
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.registered_at != FORGED
        assert row.logs[0].org_id == row.org_id
        assert row.logs[0].lead_id == row.id


def test_trigger_lifecycle(database_url, engine):
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    def trigger_count():
        with engine.connect() as conn:
            return conn.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgname='trg_sales_leads_registered_at' AND NOT tgisinternal"))
    assert trigger_count() == 1
    command.downgrade(cfg, "-1")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT to_regprocedure('sales_leads_guard_registered_at()')")) is None
    assert trigger_count() == 0
    command.upgrade(cfg, "head")
    assert trigger_count() == 1


def test_orm_cross_org_assignment_rejected_not_silently_rewritten(ready):
    with Session(ready) as session:
        row = SalesLead(**lead())
        wrong = SalesLeadOwnerLog(org_id=OTHER, action="register")
        row.logs.append(wrong)
        session.add(row)
        with pytest.raises(IntegrityError, match="fk_sales_lead_owner_logs_org_lead"):
            session.commit()
        session.rollback()
