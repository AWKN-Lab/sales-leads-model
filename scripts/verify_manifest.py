#!/usr/bin/env python3
"""校验交付文件完整性（对照 MANIFEST.sha256）。"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = ROOT / "MANIFEST.sha256"
if not manifest.exists():
    print("❌ 缺 MANIFEST.sha256")
    sys.exit(1)

bad = missing = ok = 0
for line in manifest.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    digest, rel = line.split(None, 1)
    path = ROOT / rel.strip()
    if not path.exists():
        print(f"  ❌ 缺失: {rel}")
        missing += 1
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        print(f"  ❌ 不一致: {rel}")
        bad += 1
    else:
        ok += 1
print(f"完整性校验: {ok} 个一致, {bad} 个不一致, {missing} 个缺失")
sys.exit(1 if (bad or missing) else 0)
