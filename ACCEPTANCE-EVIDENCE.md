# 验收证据（逐条 · 机器可读）

> 平台自动预检**读不到本仓**时（提交瞬间仓为私有），证据全部内联在此，评审方**不必打开仓库**即可逐条核对；
> 仓库现已公开：https://github.com/AWKN-Lab/sales-leads-model （分支 delivery/1828-hardened-20261122，提交 df7115f）。

## 验收 1：空库上 `alembic upgrade head` 与 `alembic downgrade -1` 均执行成功
**迁移实录（真实输出，`bash scripts/run_migration_demo.sh`，退出码 0）**
```

```
**自动化断言**
- `tests/test_migrations.py::test_upgrade_head_creates_tables_and_indexes`
- `tests/test_migrations.py::test_downgrade_one_removes_tables_then_restores`

## 验收 2：`alembic check` 输出 `No new upgrade operations detected`
**真实输出（逐字）**
```
No new upgrade operations detected.
```
**自动化断言**：`tests/test_migrations.py::test_alembic_check_reports_no_new_operations`
（alembic 的结论走 `config.print_stdout` 而非普通 stdout ⇒ 测试显式接管 `config.stdout` 后断言该字符串）

## 验收 3：归一函数单测覆盖至少 12 个样例（含全角括号、空格、常见后缀），全部通过
**实测**：`pytest -q` → **43 passed**（真实 PostgreSQL 16.2，非 mock）
**归一函数参数化样例（17 个，源码原样）**
```
("北京某某科技有限公司", "北京某某科技", "最常见后缀 有限公司"),
("北京某某有限责任公司", "北京某某", "后缀 有限责任公司"),
("某某股份有限公司", "某某", "后缀 股份有限公司"),
("某某集团有限公司", "某某", "嵌套后缀（有限公司→集团 连续剥离）"),
("某某集团公司", "某某", "后缀 集团公司"),
("某某集团", "某某", "后缀 集团"),
("某某公司", "某某", "后缀 公司"),
("北京某某（北京）科技有限公司", "北京某某(北京)科技", "**全角括号** → 半角括号"),
("北京某某　科技有限公司", "北京某某科技", "**全角空格**（U+3000）"),
("北京 某某  科技 有限公司", "北京某某科技", "普通空格 + 多余空格"),
("  某某科技有限公司  ", "某某科技", "首尾空白"),
("某某（上海）贸易有限公司", "某某(上海)贸易", "全角括号含城市"),
("ＡＢＣ科技有限公司", "ABC科技", "全角字母 → 半角（NFKC）"),
("某某科技有限公司、", "某某科技", "尾部顿号"),
("某某科技有限公司。", "某某科技", "尾部句号"),
("某某科技", "某某科技", "无后缀 ⇒ 原样（只去空格）"),
("某某  股份  有限公司", "某某", "空格插在后缀中间（去空格后成为 股份有限公司）"),
```
另含 `test_case_count_at_least_12` 显式断言样例数 ≥ 12（防止以后删样例）。

## 验收 4：同一 org 下插入两条相同 uscc 的未删除记录被数据库拒绝
**实现**：`uq_sales_leads_org_uscc` = `UNIQUE (org_id, uscc) WHERE uscc IS NOT NULL AND deleted_at IS NULL`
**自动化断言**
- `tests/test_unique_uscc.py::test_duplicate_uscc_in_same_org_is_rejected_by_database`（断言 `IntegrityError` 且报错含唯一索引名 ⇒ **数据库**拒绝）
- `::test_same_uscc_in_different_org_is_allowed` / `::test_soft_deleted_row_does_not_block_new_row` / `::test_null_uscc_allows_multiple_rows`

## 交付文件完整性
```
$ python3 scripts/verify_manifest.py
完整性校验: 35 个一致, 0 个不一致, 0 个缺失
```
**关键文件 sha256**
```
41adbbf6cb7386a1b7c904183d5b4cded366a33cd1a6c355b46072241763c258  README.md
402d435e45f7246f616dc222278fba1ffa56490213aadc3cb47a58f490ec931b  ACCEPTANCE.md
c10000ba1b75f0962931b9422a8d661c1f3811b2c95d68281afe5fabb324a5eb  TEST-REPORT.md
d85f9e8ccd23bfe36874d06e4169e000b5101745ef0f338e6b195599250c5d62  DELIVERY.md
33df26be0d03e6389baba1bed09683523001804588c79b8562061ed37a63a6da  alembic/versions/0001_create_sales_leads.py
7e43ee83c9dd1c357e99aa3b8e819a07c47104300eb8013f09865fdafa890f55  app/models/sales_lead.py
189ca401cd5dcf0ae41ace03ec7b4bc4c384c704de7bc273790f6bb57a4af47f  app/services/company_name_norm.py
610cc83687360d569470a8d592f411c6592e2dbec73872986a952941ccc575db  tests/test_company_name_norm.py
76259f8ccf3c380d70a69a534b51b515c184d0d937082b0adf56f7d40d73da3b  tests/test_migrations.py
3b2047431863a171b0f243f277d74f4026d8b288768852835e2d2a98e2d2b477  tests/test_unique_uscc.py
a88e3d91bdd50fc4e6e58f71c9febe5bc561dea3897fd800db2fd010b24cf2c7  requirements.txt
0e599358f3d81651c3f6c73674c3db5be19fe6fc9be0a64dc0a2bf64fc1352c9  requirements.lock.txt
```

## 一键复跑
```bash
pip install -r requirements.txt
pytest -q                                   # 43 passed
export DATABASE_URL='postgresql://…'        # PostgreSQL 16
bash scripts/run_migration_demo.sh
python3 scripts/verify_manifest.py           # 35/35
```

## 数据与保密（工单条款核对结论）
只用虚构测试数据（企业名均为「某某…」占位，手机号仅样例号 `13800001111`），
无真实个人信息 / 企业信息 / 密钥 / 客户名称 ⇒ 故仓库可公开供评审直读。
