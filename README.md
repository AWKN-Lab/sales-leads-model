# sales-leads-model — 招商线索数据模型与迁移

**ClawHunt 工单 #1828（【S3-SALES-001】招商线索、归属日志与报备字段的数据模型及迁移）交付物**

一句话：SQLAlchemy 2 + Alembic 建好招商线索的**基础表**（`sales_leads`）与**归属日志**
（`sales_lead_owner_logs`），含 4 个索引（含**同 org 同 uscc 的部分唯一索引**）、
**企业名归一函数**（独立模块 + 单测）与**字段说明**。

技术栈按统一技术约定：Python 3.11+ / SQLAlchemy 2 / Alembic / PostgreSQL 16。
配置与密钥**只从环境变量读取**；不引入任何境外 SDK；依赖 S2-IAM 的地方用**接口桩**并在本文写明对接点。

---

## 一、一键复跑

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt   # 国内镜像（直连被墙时）

# 起一个本地 PostgreSQL 16（pgserver 内嵌实例，测试会自己起一个）
pytest -q                                   # 32 项全绿

# 迁移实录（空库 → upgrade head → check → downgrade -1 → upgrade head）
export DATABASE_URL='postgresql://postgres:@/postgres?host=/path/to/pgdata'
bash scripts/run_migration_demo.sh         # 输出即 docs/migration-demo.log
```

**实测输出（2026-11-22，Python 3.11.9 / PostgreSQL 16 / SQLAlchemy 2.1.9 / Alembic 1.20.1）**

| 命令 | 期望 | 实测 |
|---|---|---|
| `pytest -q` | 全绿 | `32 passed, 8 warnings in 5.09s` |
| `alembic upgrade head` | 成功 | `Running upgrade  -> 0001_sales_leads, create sales_leads（招商线索 + 归属日志）` |
| `alembic check` | 无差异 | `No new upgrade operations detected.` |
| `alembic downgrade -1` | 成功 | `Running downgrade 0001_sales_leads -> , create sales_leads…`（两表与索引全部清理） |

> 完整实录：`docs/migration-demo.log`；渲染图：`docs/screenshots/migration-demo.png`、`docs/screenshots/pytest-demo.png`。

## 二、字段说明

### 统一字段（两表共有）
| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键，DB 侧 `gen_random_uuid()` 默认值 |
| `org_id` | UUID | 租户/机构（**必填**，多租户隔离的第一维度） |
| `site_id` | UUID | 园区/会所（可空） |
| `created_at` / `updated_at` | timestamptz | 创建/更新时间（服务端写入） |
| `created_by` | UUID | 创建人（S2-IAM 用户） |
| `deleted_at` | timestamptz | **软删除**标记（为空即未删除） |

### 表 `sales_leads`（招商线索）
| 字段 | 类型 | 空 | 说明 |
|---|---|---|---|
| `company_name` | varchar(200) | 否 | 企业名原文 |
| `company_name_norm` | varchar(200) | 否 | **归一名**：去空格 + 全角转半角 + 去常见后缀（见下） |
| `uscc` | varchar(18) | 是 | 统一社会信用代码；非空时**长度必须 18**（CHECK） |
| `industry` | varchar(64) | 是 | 行业 |
| `headcount_range` | varchar(16) | 是 | 规模：`1-10` / `11-50` / `51-200` / `200+`（CHECK 枚举） |
| `source_channel` | varchar(24) | 否 | 来源：`website_form` / `mini_program` / `referral` / `event` / `walk_in` / `inbound_call` / `other`（CHECK 枚举） |
| `contact_name` | varchar(64) | 是 | 联系人 |
| `contact_mobile_enc` | text | 是 | 手机号**密文**（AES-GCM 应用层加密，base64(nonce‖密文)） |
| `contact_mobile_hash` | varchar(64) | 是 | 手机号**检索摘要**（HMAC-SHA256，密钥取环境变量），用于等值检索 |
| `intent_space_type` | varchar(32) | 是 | 意向空间类型 |
| `intent_seats` | int | 是 | 意向工位数 |
| `owner_id` | UUID | 是 | 归属人；**公海时为空** |
| `pool_status` | varchar(8) | 否 | `owned` / `public`（CHECK 枚举，默认 `public`） |
| `stage` | varchar(32) | 否 | 阶段（默认 `new`） |
| `registered_at` | timestamptz | 否 | **报备时间**，DB 侧 `now()` 默认值 ⇒ **只由服务端写入**，不接受客户端传入 |
| `assigned_at` | timestamptz | 是 | 最近一次归属时间 |
| `last_follow_up_at` | timestamptz | 是 | 最近跟进时间 |
| `recycle_count` | int | 否 | 回流次数（默认 0，CHECK ≥ 0） |
| `lost_reason` | text | 是 | 丢单原因 |

### 表 `sales_lead_owner_logs`（归属日志）
| 字段 | 类型 | 说明 |
|---|---|---|
| `lead_id` | UUID | 所属线索（FK → `sales_leads.id`，`ON DELETE CASCADE`） |
| `action` | varchar(16) | `register` / `assign` / `claim` / `release` / `recycle` / `transfer`（CHECK 枚举） |
| `from_owner_id` / `to_owner_id` | UUID | 变更前后归属人（可空） |
| `reason` | text | 原因 |
| `operated_by` | UUID | 操作人（S2-IAM 用户） |
| `operated_at` | timestamptz | 操作时间（DB 默认 `now()`） |

### 索引
| 索引 | 定义 | 用途 |
|---|---|---|
| `uq_sales_leads_org_uscc` | UNIQUE `(org_id, uscc)` **WHERE `uscc IS NOT NULL AND deleted_at IS NULL`** | 同 org 同 uscc 的**未删除**记录唯一（**部分唯一索引**：软删除后不占键；不同 org 互不冲突） |
| `ix_sales_leads_org_company_norm` | `(org_id, company_name_norm)` | 归一名检索 / 查重 |
| `ix_sales_leads_org_mobile_hash` | `(org_id, contact_mobile_hash)` | 按手机号检索 |
| `ix_sales_leads_org_site_owner_stage` | `(org_id, site_id, owner_id, stage)` | 工作台列表（按园区/归属/阶段筛选） |
| `ix_sales_lead_owner_logs_lead` | `(org_id, lead_id, operated_at)` | 归属变更时间线 |

## 三、企业名归一（`app/services/company_name_norm.py`）

规则：**全角转半角（NFKC）→ 去所有空白 → 去首尾标点 → 剥常见后缀**。
后缀分两层：法定形式（`股份有限公司` / `有限责任公司` / `集团公司` / `有限公司`）优先，
其次软后缀（`集团` / `公司`）；**可重复剥离**（"某某集团有限公司" → "某某集团" → "某某"），
且**剥完不足 2 字就不剥**（"有限公司" 不会被剥成空）。

```python
from app.services.company_name_norm import normalize_company_name
normalize_company_name("北京某某（北京）  科技有限公司")   # → '北京某某(北京)科技'
normalize_company_name("某某集团有限公司")                  # → '某某'
```

## 四、密钥与环境变量

| 变量 | 用途 | 必填 |
|---|---|---|
| `DATABASE_URL` | 数据库连接串 | 迁移/测试必填 |
| `LEAD_MOBILE_HASH_KEY` | 手机号 HMAC-SHA256 密钥 | 用到检索摘要时必填 |
| `LEAD_MOBILE_ENC_KEY` | 手机号 AES-GCM 密钥（32 字节） | 用到加密时必填 |

> 密钥**只从环境变量读取**，代码与配置文件中都没有默认值（缺变量直接抛错，不静默降级）。

## 五、**对接点**（依赖其它工单的接口，用桩/mock 先行）

| 现在（桩） | 换成真实实现 |
|---|---|
| `app/identity.py::get_identity(user_id)` —— 返回 `user_id / tenant_id / can_view_group` | S2-IAM 的身份与数据范围接口（预计 `GET /api/v1/iam/users/{id}` 与 `/data-scope`） |
| `app/models/sales_lead.py` 的 `owner_id` / `created_by` 用 UUID 占位 | S2-IAM 的真实用户主键（结构不变，只是 id 口径对齐） |
| 归属变更写 `sales_lead_owner_logs` 由业务代码调用 | 业务员工作台的归属流转接口落库（本表即其数据源） |

替换 `app/identity.py` 一个文件即可，业务代码不动。

## 六、数据与合规

- 全部为**虚构测试数据**（"某某科技有限公司"、示例 uscc），**不含任何真实个人信息或企业信息**。
- 手机号只以**密文 + HMAC 摘要**落库，测试里用的是样例号 `13800001111`。
- 未引入任何向境外发送数据的第三方 SDK；依赖仅 SQLAlchemy / Alembic / psycopg / pgserver / pytest / cryptography。

## 七、已知限制（如实）

- 本单只交付**数据模型与迁移**，不含业务接口（FastAPI 路由）与前端。
- `registered_at` 由 DB 默认值写入（`now()`）；若后续要求"以报备动作发生时刻为准"，
  应改为由服务端显式赋值（当前实现已保证客户端无法覆盖）。
- `stage` 取值为字符串（默认 `new`），本单未给出枚举清单 ⇒ 未加 CHECK；工单补充枚举后需新增迁移。

## 八、复跑清单（给验收方）

```bash
pip install -r requirements.txt
pytest -q                                  # 32 项
DATABASE_URL=... bash scripts/run_migration_demo.sh   # 迁移实录
python scripts/verify_manifest.py          # 校验交付文件完整性（MANIFEST.sha256）
```
