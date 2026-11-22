# 交标说明（#1828）

## 交付物清单

| 文件 | 内容 |
|---|---|
| `app/models/base.py` | 声明式基类 + 统一字段（UUID 主键 / org_id / site_id / 审计 / 软删除） |
| `app/models/sales_lead.py` | `SalesLead`（26 列）+ `SalesLeadOwnerLog`（14 列）+ 5 个索引 + CHECK 约束 |
| `app/services/company_name_norm.py` | 企业名归一函数（独立模块） |
| `app/services/mobile.py` | 手机号 HMAC 检索摘要 + AES-GCM 应用层加密（密钥取环境变量） |
| `app/identity.py` | S2-IAM **接口桩**（对接点见 README） |
| `app/db.py` | 引擎 / 会话工厂（连接串取环境变量） |
| `alembic/versions/0001_create_sales_leads.py` | 迁移脚本（含**对称 downgrade**） |
| `tests/` | 32 项测试（归一 21 / 迁移 4 / 唯一索引 4 / 手机号 3） |
| `scripts/run_migration_demo.sh` | 迁移实录脚本（真实输出落 `docs/migration-demo.log`） |
| `scripts/render-logs.mjs` | 把终端实录渲染成验收截图（开发期工具） |
| `docs/migration-demo.log`、`docs/pytest-demo.log` | **真实运行输出** |
| `docs/screenshots/migration-demo.png`、`pytest-demo.png` | 上两者的渲染图 |
| `README.md` / `ACCEPTANCE.md` / `TEST-REPORT.md` / `DELIVERY.md` | 安装运行说明 / 逐条验收证据 / 测试报告 / 本文件 |
| `MANIFEST.sha256` | 交付文件完整性校验清单 |

## 一键复跑

```bash
pip install -r requirements.txt
pytest -q                                   # 32 passed
export DATABASE_URL='postgresql://postgres:@/postgres?host=/path/to/pgdata'
bash scripts/run_migration_demo.sh          # upgrade head → check → downgrade -1 → upgrade head
python scripts/verify_manifest.py           # MANIFEST.sha256 完整性校验
```

## 验收对照（详见 ACCEPTANCE.md）

| 验收标准 | 结论 |
|---|---|
| 1. 空库 `upgrade head` 与 `downgrade -1` 均成功 | ✅ 实录在 `docs/migration-demo.log`，并有 2 个自动化用例断言 |
| 2. `alembic check` 输出 `No new upgrade operations detected` | ✅ 实录可见 + 用例断言输出字符串 |
| 3. 归一函数单测 ≥ 12 个样例且全部通过 | ✅ 21 项（含全角括号 / 全角空格 / 常见后缀），另加"样例数 ≥ 12"自检 |
| 4. 同 org 同 uscc 的未删除记录被 DB 拒绝 | ✅ 用例断言 `IntegrityError` 且报错含唯一索引名；另覆盖跨 org 允许、软删除不占键、空值允许 |

## 限制（如实）

- 本单只交付**模型与迁移**，不含 FastAPI 接口与前端。
- `stage` 未加枚举 CHECK（工单未给枚举清单），后续补充需新增迁移。
- 密钥必须由环境变量提供（无默认值），部署方需自行注入 `LEAD_MOBILE_HASH_KEY` / `LEAD_MOBILE_ENC_KEY`。
