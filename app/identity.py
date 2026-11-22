"""
S2-IAM（身份、角色与数据范围）**接口桩**。

对接点（真实实现到位后替换本文件即可，业务代码不动）：
  - 真实接口预计为 `GET /api/v1/iam/users/{user_id}` 与 `GET /api/v1/iam/users/{user_id}/data-scope`；
  - 本仓库只用它回答两个问题：**当前写入者是谁**（created_by / operated_by）、
    **能不能看集团维度**（数据范围）。故这里给出最小可用桩。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    user_id: str
    tenant_id: str
    can_view_group: bool = False


#: 演示用身份（测试与 mock 数据用；真实环境从鉴权中间件注入）
DEMO_IDENTITY = Identity(user_id="00000000-0000-0000-0000-000000000001", tenant_id="00000000-0000-0000-0000-0000000000aa", can_view_group=True)


def get_identity(user_id: str | None = None) -> Identity:
    """接口桩：按 user_id 返回身份；未知用户返回演示身份。"""
    if not user_id:
        return DEMO_IDENTITY
    return Identity(user_id=user_id, tenant_id=DEMO_IDENTITY.tenant_id, can_view_group=DEMO_IDENTITY.can_view_group)
