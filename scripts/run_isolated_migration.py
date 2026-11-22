"""在自建临时 PostgreSQL 实例执行迁移门禁；不使用外部 DATABASE_URL。"""
import os
import pathlib
import subprocess
import sys
import tempfile
import pgserver
from sqlalchemy import create_engine, text

root = pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="sales-leads-migration-") as directory:
    db = pgserver.get_server(directory)
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = db.get_uri()
        env["PATH"] = str(pathlib.Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        engine = create_engine(env["DATABASE_URL"])
        try:
            with engine.connect() as conn:
                print("PostgreSQL actual version:", conn.scalar(text("SHOW server_version")), flush=True)
                assert conn.scalar(text("SHOW server_version_num")).startswith("16")
        finally:
            engine.dispose()
        subprocess.run(["bash", "scripts/run_migration_demo.sh"], cwd=root, env=env, check=True)
        print("MIGRATION_EXIT=0", flush=True)
    finally:
        db.cleanup()
