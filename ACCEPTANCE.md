# #1828 验收
| 验收项 | 证据 |
|---|---|
| 空库升级和降级 | tests/test_migrations.py、docs/migration-demo.log |
| alembic check 无新增操作 | tests/test_migrations.py、docs/migration-demo.log |
| 企业名归一至少12例 | tests/test_company_name_norm.py，21项 |
| 同 org 未删除 USCC 唯一 | tests/test_unique_uscc.py，4项（含跨组织、软删除及空值） |
| 手机号加密及 HMAC | tests/test_mobile.py，3项 |
| 组织关联、状态约束、报备时间 | tests/test_hardening.py，11项真实 PG 回归 |
全量43项；运行和结果见 TEST-REPORT.md、docs/pytest-demo.log。组合外键由模型和迁移同时定义，报备触发器由迁移定义，以数据库实际行为验证。旧 0001 已部署的数据库须另行增量迁移。
