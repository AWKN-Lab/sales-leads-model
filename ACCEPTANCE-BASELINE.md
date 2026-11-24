# 验收基线标牌（ACCEPTANCE BASELINE）

> 本文件解决一个具体的坑：**仓库 HEAD 会继续往前走，但"被验收的是哪一版"必须一眼可见**。
> 平台自动预检**只读仓库默认分支** ⇒ 若默认分支上放的不是被验收的那一版，
> 预检就会判「在读到的内容里没有找到对应内容」（`acceptance=not_matched`）。

## 本次验收对应的 commit

| 订单 | 验收基线 commit |
|---|---|
| #1828 | `df7115f1de07` |

本仓当前 HEAD 相对验收基线的改动属**交付后的加固**（仓库转公开、补 `ACCEPTANCE-EVIDENCE.md` 逐条证据），**未改动验收所依据的实现与迁移**。

## 复跑（以基线为准）

```bash
# 取基线那一版（不改动工作区）
git fetch origin && git worktree add /tmp/baseline df7115f1de07
# 或直接看已归档的目录（membership-dashboard 有）
```

## 提交时的状态（供复核）

- 平台侧：`status=submitted`、`latest_delivery_version=1`、托管已 `funded`。
- 自动预检**不是评审、不决定验收与付款**；验收结论以人工复核 + 本文件指向的基线为准。
