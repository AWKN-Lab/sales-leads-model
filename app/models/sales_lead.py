"""
招商线索模型（表 sales_leads）与归属日志（表 sales_lead_owner_logs）。

字段口径见 README「字段说明」。金额类字段本表没有（招商线索不含金额）——
若后续工单引入金额，一律以「分」存整数（统一技术约定）。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantMixin

#: 规模区间枚举
HEADCOUNT_RANGES = ("1-10", "11-50", "51-200", "200+")

#: 来源渠道枚举
SOURCE_CHANNELS = (
    "website_form",
    "mini_program",
    "referral",
    "event",
    "walk_in",
    "inbound_call",
    "other",
)

#: 公海 / 归属状态
POOL_STATUSES = ("owned", "public")

#: 归属动作
OWNER_LOG_ACTIONS = ("register", "assign", "claim", "release", "recycle", "transfer")


class SalesLead(Base, TenantMixin):
    """招商线索（基础表，供本模块其余工单复用）。"""

    __tablename__ = "sales_leads"
    __table_args__ = (
        # 统一社会信用代码：可空，填了就必须是 18 位
        CheckConstraint("uscc IS NULL OR char_length(uscc) = 18", name="ck_sales_leads_uscc_len"),
        CheckConstraint(
            "headcount_range IS NULL OR headcount_range IN ('1-10','11-50','51-200','200+')",
            name="ck_sales_leads_headcount_range",
        ),
        CheckConstraint(
            "source_channel IN ('website_form','mini_program','referral','event','walk_in','inbound_call','other')",
            name="ck_sales_leads_source_channel",
        ),
        CheckConstraint("pool_status IN ('owned','public')", name="ck_sales_leads_pool_status"),
        CheckConstraint("recycle_count >= 0", name="ck_sales_leads_recycle_count"),
        # 同一 org 下相同 uscc 且未软删除 ⇒ 唯一（部分唯一索引）
        Index(
            "uq_sales_leads_org_uscc",
            "org_id",
            "uscc",
            unique=True,
            postgresql_where=text("uscc IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_sales_leads_org_company_norm", "org_id", "company_name_norm"),
        Index("ix_sales_leads_org_mobile_hash", "org_id", "contact_mobile_hash"),
        Index("ix_sales_leads_org_site_owner_stage", "org_id", "site_id", "owner_id", "stage"),
    )

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name_norm: Mapped[str] = mapped_column(String(200), nullable=False)
    uscc: Mapped[str | None] = mapped_column(String(18), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    headcount_range: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(24), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_mobile_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_mobile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    intent_space_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    pool_status: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'public'"))
    stage: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'new'"))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recycle_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lost_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    logs: Mapped[list["SalesLeadOwnerLog"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class SalesLeadOwnerLog(Base, TenantMixin):
    """归属变更日志：每次归属变化记一条（登记 / 指派 / 认领 / 释放 / 回流 / 转移）。"""

    __tablename__ = "sales_lead_owner_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('register','assign','claim','release','recycle','transfer')",
            name="ck_sales_lead_owner_logs_action",
        ),
        Index("ix_sales_lead_owner_logs_lead", "org_id", "lead_id", "operated_at"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sales_leads.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    from_owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    to_owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    operated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lead: Mapped[SalesLead] = relationship(back_populates="logs")
