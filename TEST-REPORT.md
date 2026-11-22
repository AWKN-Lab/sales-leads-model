# 测试报告（#1828）

- 环境：Linux / Python 3.11.9 / SQLAlchemy 2.1.9 / Alembic 1.20.1 / **PostgreSQL 16（pgserver 内嵌实例，真实数据库，非 mock）**
- 时间：2026-11-22
- 命令：`pytest -q` ⇒ **32 passed, 8 warnings in 5.09s**（完整输出：`docs/pytest-demo.log`，渲染图：`docs/screenshots/pytest-demo.png`）

## 用例清单

| 文件 | 用例 | 覆盖的验收点 |
|---|---|---|
| `tests/test_company_name_norm.py` | 21（17 个参数化样例 + 4 个专项） | 验收 3：全角括号 / 空格 / 常见后缀；样例数 ≥ 12 的自检 |
| `tests/test_migrations.py` | 4 | 验收 1（upgrade head / downgrade -1）、验收 2（alembic check）、模型与库一致性 |
| `tests/test_unique_uscc.py` | 4 | 验收 4：同 org 同 uscc 被 DB 拒绝；跨 org 允许；软删除不占键；空 uscc 允许 |
| `tests/test_mobile.py` | 3 | 手机号 HMAC / AES-GCM 加解密、密钥只从环境变量读取 |

## 迁移实录（真实输出）

`docs/migration-demo.log`（渲染图 `docs/screenshots/migration-demo.png`）：

```
$ alembic upgrade head
    INFO  [alembic.runtime.migration] Running upgrade  -> 0001_sales_leads, create sales_leads（招商线索 + 归属日志）
$ alembic check
    No new upgrade operations detected.
$ alembic downgrade -1
    INFO  [alembic.runtime.migration] Running downgrade 0001_sales_leads -> , create sales_leads（招商线索 + 归属日志）
$ alembic upgrade head
    INFO  [alembic.runtime.migration] Running upgrade  -> 0001_sales_leads, create sales_leads（招商线索 + 归属日志）
```

## 变异自证（3/3 因正确原因变红）

| 变异 | 变红用例 | 失败信息 |
|---|---|---|
| M1 不剥法定形式后缀 | 归一测试 13 个参数化用例 | `AssertionError: 最常见后缀 有限公司` |
| M2 不删空白 | 归一测试 6 个 | `AssertionError: **全角空格**（U+3000）` |
| M3 部分唯一索引丢掉「未软删除」条件 | `test_model_and_database_agree_on_partial_index_condition` | `AssertionError: 模型与库的部分索引条件不一致：模型='uscc IS NOT NULL' 库='((uscc IS NOT NULL) AND (deleted_at IS NULL))'` |

复原校验：三次均 ✅ 字节一致（sha256）；复原后全量 `32 passed`。

## 过程中被测试抓到的真问题（已修）

1. **归一顺序错**：先剥后缀再去标点 ⇒ "某某有限公司、" 剥不掉后缀 ⇒ 改为先去标点再剥。
2. **软后缀误伤**："有限公司" 会被剥成 "有限" ⇒ 改为法定形式优先，且剥完不足 2 字就不剥。
3. **测试自足性**：新加的"模型与库一致"用例单独跑时缺表 ⇒ 补 `command.upgrade` 前置。
4. **API 漂移**：`cryptography` 新版 `AESGCM.encrypt(nonce, data, aad)` 把 nonce 提为显式参数
   ⇒ 兼容新旧签名，并补拼 nonce（否则解密 `InvalidTag`）。
5. **`alembic check` 盲区**：它不比较部分索引条件 ⇒ 补模型↔库一致性断言（M3 就是靠它抓到的）。
