# #1828 最终整改复测
环境：161，Python 3.11.13，PostgreSQL 16.2（pgserver 0.1.4），SQLAlchemy 2.1.9，Alembic 1.20.1，pytest 9.2.0，cryptography 50.0.2。依赖锁见 requirements.lock.txt。
- 原版 32 项在独立副本通过。旧原始日志实际为 31 项，与旧报告不一致；本版以新原始输出为准。
- 原版加入 10 项约束回归：10 failed，退出码 1（docs/evidence/baseline-regression.log）。
- 初次整改后追加 ORM 错误租户关联测试：1 failed，退出码 1（docs/evidence/orm-regression.log）。
- 修复完成后：43 项全绿，0 failed/error，退出码 0；1 条 XDG_RUNTIME_DIR 提示，不影响测试。
- 真实空库迁移 upgrade head / check / downgrade -1 / upgrade head；独立输出见 docs/migration-demo.log。
- 11 项新增回归覆盖组织外键、ORM 同步、归属状态、伪造和修改报备时间、普通更新、触发器升降级。
- docs/screenshots 是实录文本渲染，原始日志为主证据。
- 初始迁移只用于空库；真实 IAM 与业务接口待集成。无平台交标或客户验收。
