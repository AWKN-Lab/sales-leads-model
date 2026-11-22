#!/usr/bin/env node
/** 把终端实录渲染成验收截图（docs/screenshots/*.png）—— 真实运行输出，不是摆拍。 */
import { readFileSync, mkdirSync, existsSync } from 'node:fs'
import { join } from 'node:path'

// playwright-core 是**开发期**工具（只用来把终端实录渲染成图）。
// 若本仓未安装 node 依赖，可用 PLAYWRIGHT_CORE_PATH 指向别处的模块入口。
const PW = process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core'
const pwMod = await import(PW)
const chromium = pwMod.chromium ?? pwMod.default?.chromium
if (!chromium) throw new Error(`playwright-core 载入失败：${PW}`)

const EXEC = '/root/.cache/ms-playwright/chromium-1243/chrome-linux/chrome'
const OUT = join(process.cwd(), 'docs', 'screenshots')
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true })

const jobs = [
  ['docs/migration-demo.log', 'migration-demo.png', 'alembic 迁移实录（upgrade head / check / downgrade -1 / upgrade head）'],
  ['docs/pytest-demo.log', 'pytest-demo.png', 'pytest 实测输出（真实 PG16 实例）'],
]

const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
for (const [src, out, title] of jobs) {
  if (!existsSync(src)) { console.log(`  ⚠️ 缺少 ${src}，跳过`); continue }
  const text = readFileSync(src, 'utf-8')
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#0d1117;color:#c9d1d9;font-family:"DejaVu Sans Mono",monospace;font-size:13px;line-height:1.55}
    .wrap{padding:22px 26px}
    h1{font-size:15px;color:#58a6ff;margin:0 0 14px;font-weight:600}
    pre{margin:0;white-space:pre-wrap;word-break:break-all}
    .ok{color:#3fb950}.warn{color:#d29922}.err{color:#f85149}.info{color:#8b949e}
  </style></head><body><div class="wrap"><h1>${title}</h1><pre>${
    text.replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/No new upgrade operations detected\./g, '<span class="ok">No new upgrade operations detected.</span>')
        .replace(/passed/g, '<span class="ok">passed</span>')
        .replace(/failed/g, '<span class="err">failed</span>')
        .replace(/^(\$ .*)$/gm, '<span class="info">$1</span>')
  }</pre></div></body></html>`
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 }, deviceScaleFactor: 2 })
  await page.setContent(html)
  await page.waitForTimeout(200)
  await page.screenshot({ path: join(OUT, out), fullPage: true })
  console.log(`  ✅ docs/screenshots/${out}`)
  await page.close()
}
await browser.close()
