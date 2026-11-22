# 验收逐条证据（#1828）

> 每条验收标准 ⇒ 对应实现位置 + **可复跑的验证命令** + 实测输出。
> 真实运行日志：`docs/migration-demo.log`、`docs/pytest-demo.log`（渲染图见 `docs/screenshots/`）。

## 验收 1：空库上 `alembic upgrade head` 与 `alembic downgrade -1` 均执行成功

- 实现：`alembic/versions/0001_create_sales_leads.py`（`upgrade()` 建两表 + 5 个索引 + CHECK/FK；
  `downgrade()` **对称清理**：先删索引（含部分唯一索引的 `postgresql_where`）、再删表）
- 验证命令：
  ```bash
  export DATABASE_URL='postgresql://postgres:@/postgres?host=/path/to/pgdata'
  alembic upgrade head && alembic downgrade -1
  ```
- 实测（`docs/migration-demo.log`）：
  ```
  $ alembic upgrade head
      INFO  [alembic.runtime.migration] Running upgrade  -> 0001_sales_leads, create sales_leads（招商线索 + 归属日志）
  $ alembic downgrade -1
      INFO  [alembic.runtime.migration] Running downgrade 0001_sales_leads -> , create sales_leads（招商线索 + 归属日志）
  ```
- 自动化断言：`tests/test_migrations.py::test_upgrade_head_creates_tables_and_indexes`
  （表与 4 个业务索引齐全、部分唯一索引确为 `unique=True` 且带条件）
  与 `::test_downgrade_one_removes_tables_then_restores`（降级后表消失、再次升级可复原）。

## 验收 2：`alembic check` 输出 `No new upgrade operations detected`

- 验证命令：`alembic check`
- 实测（`docs/migration-demo.log`）：
  ```
  $ alembic check
      INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
      No new upgrade operations detected.
  ```
- 自动化断言：`tests/test_migrations.py::test_alembic_check_reports_no_new_operations`
  —— 显式接管 `config.stdout` 后断言输出含该结论（**alembic 的结论走 `config.print_stdout`，
  不是普通 stdout ⇒ 必须显式接管**）。
- ⚠️ **已知盲区（已补断言）**：`alembic check` **不比较索引的部分索引条件**（`postgresql_where`），
  模型漂移它也不报 ⇒ 另有
  `::test_model_and_database_agree_on_partial_index_condition` 断言模型与库的条件**逐字一致**
  （归一化空白与括号后比较）。

## 验收 3：归一函数单测覆盖至少 12 个样例（含全角括号、空格、常见后缀），全部通过

- 实现：`app/services/company_name_norm.py::normalize_company_name`
- 样例数：**17 个参数化样例 + 4 个专项用例 = 21 项**（`tests/test_company_name_norm.py`）
  其中含：全角括号 `北京某某（北京）科技有限公司`、全角空格 `U+3000`、全角字母 `ＡＢＣ`、
  多余空格、首尾空白、尾部标点、常见后缀（有限公司/有限责任公司/股份有限公司/集团公司/集团/公司）、
  后缀嵌在空格中间。
- 验证命令：`pytest -q tests/test_company_name_norm.py` → 实测 `21 passed`
- 另有 `test_case_count_at_least_12` 显式断言样例数 ≥ 12（**防止以后有人删样例**）。

## 验收 4：同一 org 下插入两条相同 uscc 的未删除记录被数据库拒绝（测试用例）

- 实现：部分唯一索引 `uq_sales_leads_org_uscc`：
  `UNIQUE (org_id, uscc) WHERE uscc IS NOT NULL AND deleted_at IS NULL`
- 测试：`tests/test_unique_uscc.py`
  - `::test_duplicate_uscc_in_same_org_is_rejected_by_database` —— 同 org 同 uscc 第二条
    **由数据库拒绝**（`IntegrityError`，且报错里含唯一索引名 / `duplicate key`）
  - `::test_same_uscc_in_different_org_is_allowed` —— 不同 org 互不冲突（多租户隔离）
  - `::test_soft_deleted_row_does_not_block_new_row` —— 已软删除的同 uscc 记录**不占唯一键**
  - `::test_null_uscc_allows_multiple_rows` —— uscc 可空 ⇒ 多条空 uscc 不冲突
- 实测：`pytest -q` → `32 passed`

## 变异自证（证明测试能失败）

改**行为**不改名，测试必须**因正确原因**变红，改完当场按 sha256 复原：

| 变异 | 变红用例 | 失败原因（实测） |
|---|---|---|
| M1 归一函数不剥法定形式后缀 | `tests/test_company_name_norm.py::test_normalize[…]`（13 个参数化用例） | `AssertionError: 最常见后缀 有限公司` |
| M2 归一函数不删空白 | `tests/test_company_name_norm.py::test_normalize[…全角空格…]`、`::test_equivalent_names_normalize_to_same_key` 等 6 个 | `AssertionError: **全角空格**（U+3000）` |
| M3 部分唯一索引丢掉「未软删除」条件 | `tests/test_migrations.py::test_model_and_database_agree_on_partial_index_condition` | `AssertionError: 模型与库的部分索引条件不一致：模型='uscc IS NOT NULL' 库='((uscc IS NOT NULL) AND (deleted_at IS NULL))'` |

复原校验：三次均 ✅ **字节一致**（sha256）；复原后 `pytest -q` → `32 passed`。
