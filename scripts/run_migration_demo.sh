#!/usr/bin/env bash
# 迁移实录：在**空库**上跑 upgrade head / alembic check / downgrade -1 / upgrade head，
# 输出即验收证据（docs/migration-demo.log）。
# 用法：DATABASE_URL=... bash scripts/run_migration_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:?必须设置 DATABASE_URL}"
export PYTHONUNBUFFERED=1
run() { echo "\$ $*"; "$@" 2>&1 | sed 's/^/    /'; echo; }
echo "# 迁移实录（真实输出）"
echo "# 数据库：PostgreSQL 16（pgserver 本地实例，socket 连接）"
echo "# 生成时间：$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo
run alembic upgrade head
run alembic check
run alembic downgrade -1
run alembic upgrade head
echo "# 结束：alembic check 无差异、升降级均成功"
