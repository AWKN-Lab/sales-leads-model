# #1828 修订交付候选
以161共享目录原版为基线，保留模型、企业名归一、加密、迁移及原32项测试；新增11项约束回归、依赖锁、原始证据。
交付物：app/、alembic/、tests/、requirements.txt、requirements.lock.txt、README.md、ACCEPTANCE.md、TEST-REPORT.md、docs/ 及 MANIFEST.sha256。
安装：pip install -r requirements.lock.txt；验证：python -m pytest -q；迁移实录：python scripts/run_isolated_migration.py；完整性：python scripts/verify_manifest.py。
本候选针对空库；真实 IAM / API 待集成。未提交客户。历史原始目录保持不变。
