#!/usr/bin/env python3
"""把交付仓推到 GitHub（Contents API 点亮空仓 → Git Data API 推全部 → 逐字节回读核对）。"""
import base64, hashlib, json, os, pathlib, sys, time, urllib.request, urllib.error

TOKEN = os.environ.get("GITHUB_TOKEN_REPO") or os.environ.get("GITHUB_TOKEN")
OWNER, REPO = "AWKN-Lab", "sales-leads-model"
BRANCH = "main"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {"node_modules", "dist", ".git"}
SKIP_FILES = {"tsconfig.tsbuildinfo", ".npmrc", "MANIFEST.sha256"}
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def req(method, url, payload=None, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {TOKEN}")
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("User-Agent", "clawhunt-deliver")
    if data:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=120) as resp:
        body = resp.read()
        return body if raw else json.loads(body)


def files():
    out = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if set(rel.parts) & SKIP_DIRS or rel.name in SKIP_FILES:
            continue
        out.append((rel.as_posix(), p))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--merge-main", action="store_true", help="推完后把 main 快进到该提交")
    ap.add_argument("--message", default="feat: 会员空间管理驾驶舱前端（#1851 外壳 + #1896 出租率面板）")
    args = ap.parse_args()
    branch = args.branch
    fl = files()
    print(f"  待推 {len(fl)} 个文件")

    # ① Contents API 点亮空仓（空仓不能直接建 blob）
    readme = next(p for r, p in fl if r == "README.md")
    try:
        req("PUT", f"{API}/contents/README.md", {
            "message": "chore: 交付 README（点亮空仓）",
            "content": base64.b64encode(readme.read_bytes()).decode(),
        })
        print("  ✅ README.md 已落仓（Contents API）")
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ README PUT 失败: {e.code} {e.read()[:200]}")

    time.sleep(1)
    # 分支不存在 ⇒ 从 main 开一条（保留独立分支，便于复核方对比）
    try:
        ref = req("GET", f"{API}/git/ref/heads/{branch}")
        base_commit = ref["object"]["sha"]
        print(f"  分支 {branch} 已存在，基于 {base_commit[:8]}")
    except urllib.error.HTTPError:
        main_ref = req("GET", f"{API}/git/ref/heads/main")
        base_commit = main_ref["object"]["sha"]
        req("POST", f"{API}/git/refs", {"ref": f"refs/heads/{branch}", "sha": base_commit})
        print(f"  新建分支 {branch}（基于 main {base_commit[:8]}）")
    base_tree = req("GET", f"{API}/git/commits/{base_commit}")["tree"]["sha"]
    print(f"  base commit {base_commit[:8]} / tree {base_tree[:8]}")

    # ② Git Data API：blob → tree → commit → update ref
    entries = []
    for rel, path in fl:
        blob = req("POST", f"{API}/git/blobs", {
            "content": base64.b64encode(path.read_bytes()).decode(),
            "encoding": "base64",
        })
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = req("POST", f"{API}/git/trees", {
        "base_tree": base_tree, "tree": entries, "truncate": True})
    commit = req("POST", f"{API}/git/commits", {
        "message": args.message + "\n\n"
                   "- 七个页签 + 全局筛选（筛选/页签只存 URL ⇒ 刷新保持）\n"
                   "- 卡片三态（loading/empty/error，空态不把 0 画成数据）\n"
                   "- 口径提示含定义与版本号 v1.2\n"
                   "- 出租率面板：指标卡+环比、12 月趋势、按楼层堆叠条形（图例+条内数值标签）、\n"
                   "  到期分桶、续约率趋势、点击楼层跳 /floors/:floorId?org_id=&site_id=&month=\n"
                   "- 14 项单测全绿；构建产物零外部域名；4 张验收截图\n"
                   "- 变异自证 3/3 因正确原因变红（改行为不改名，复原后 sha256 一致）",
        "tree": tree["sha"], "parents": [base_commit]})
    req("PATCH", f"{API}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": False})
    print(f"  ✅ 推送完成 分支={branch} commit {commit['sha'][:8]}")
    if args.merge_main:
        main_head = req("GET", f"{API}/git/ref/heads/main")["object"]["sha"]
        if commit["sha"] != main_head:
            req("PATCH", f"{API}/git/refs/heads/main", {"sha": commit["sha"], "force": False})
            print(f"  ✅ main 已快进到 {commit['sha'][:8]}（原 {main_head[:8]}）")

    # ③ 回读逐字节核对（独立 GET）
    head = req("GET", f"{API}/git/ref/heads/{branch}")["object"]["sha"]
    remote_tree = req("GET", f"{API}/git/trees/{req('GET', f'{API}/git/commits/{head}')['tree']['sha']}?recursive=1")
    remote = {t["path"]: t["sha"] for t in remote_tree["tree"] if t["type"] == "blob"}
    ok = bad = 0
    for rel, path in fl:
        b = req("GET", f"{API}/git/blobs/{remote[rel]}") if rel in remote else None
        if b is None:
            print(f"    ❌ {rel}: 远端缺失"); bad += 1; continue
        rb = base64.b64decode(b["content"])
        if hashlib.sha256(rb).hexdigest() == hashlib.sha256(path.read_bytes()).hexdigest():
            ok += 1
        else:
            print(f"    ❌ {rel}: 字节不一致"); bad += 1
    print(f"  回读核对: {ok}/{len(fl)} MATCH, {bad} MISMATCH")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
