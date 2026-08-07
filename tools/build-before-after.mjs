/**
 * Composes the before/after asset pairs.
 *
 * Reads the captured screenshots from assets/v1-tote-ops and
 * assets/v2-totetrack, lays each matched pair out side by side in a browser,
 * and writes the result to assets/before-after/.
 *
 * Only screens that exist in both apps are paired. Everything else stays a
 * standalone shot in its own folder — a "before" with nothing to compare it
 * against is not a before.
 *
 * Usage:
 *   npm install
 *   npx playwright install chromium
 *   npm run build:before-after
 */

import { chromium } from 'playwright'
import { mkdir, readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const ASSETS = join(ROOT, 'assets')
const OUT = join(ASSETS, 'before-after')

// Screens that exist in both apps. The rest of each app's surface has no
// counterpart, so pairing them would invent a comparison.
const PAIRS = [
  { name: 'dashboard', v1: '01-dashboard', v2: '01-dashboard', title: 'Dashboard' },
  { name: 'leads', v1: '08-leads-list', v2: '04-leads', title: 'Leads' },
  { name: 'invoices', v1: '10-invoices-list', v2: '05-invoices', title: 'Invoices' },
]

const VIEWPORTS = ['desktop-1280', 'ipad-768']

// Both panels are cropped to the same height from the top. Letting each run
// to its natural length left one side towering over the other with a large
// dead area beside it — the pair is what matters, not the full scroll of
// either side.
const PANEL_WIDTH = 900
const PANEL_HEIGHT = 1100

async function dataUri(path) {
  const buf = await readFile(path)
  return `data:image/png;base64,${buf.toString('base64')}`
}

function page(beforeSrc, afterSrc, title) {
  return `<!doctype html>
<html><head><meta charset="utf-8" /><style>
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 40px; background: #0f172a;
    font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  h1 { color: #f8fafc; font-size: 26px; margin: 0 0 28px; font-weight: 650; }
  .row { display: flex; gap: 32px; align-items: flex-start; }
  .panel { width: ${PANEL_WIDTH}px; }
  .label {
    display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px;
  }
  .tag {
    font-size: 12px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
    padding: 5px 11px; border-radius: 999px;
  }
  .tag.before { background: #7f1d1d; color: #fecaca; }
  .tag.after  { background: #064e3b; color: #a7f3d0; }
  .app { color: #94a3b8; font-size: 14px; }
  /* Clipping via a fixed-height frame rather than object-fit: cover — cover
     crops horizontally too, which sliced columns off the wider screenshot. */
  .frame {
    height: ${PANEL_HEIGHT}px; overflow: hidden; background: #f0f3f7;
    border-radius: 12px; border: 1px solid #1e293b;
    box-shadow: 0 18px 40px rgba(0,0,0,.45);
  }
  .shot { width: 100%; height: auto; display: block; }
</style></head>
<body>
  <h1>${title}</h1>
  <div class="row">
    <div class="panel">
      <div class="label"><span class="tag before">Before</span><span class="app">Tote-Ops · v1</span></div>
      <div class="frame"><img class="shot" src="${beforeSrc}" /></div>
    </div>
    <div class="panel">
      <div class="label"><span class="tag after">After</span><span class="app">ToteTrack · v2</span></div>
      <div class="frame"><img class="shot" src="${afterSrc}" /></div>
    </div>
  </div>
</body></html>`
}

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch()

for (const viewport of VIEWPORTS) {
  for (const pair of PAIRS) {
    const before = await dataUri(join(ASSETS, 'v1-tote-ops', viewport, `${pair.v1}.png`))
    const after = await dataUri(join(ASSETS, 'v2-totetrack', viewport, `${pair.v2}.png`))

    const ctx = await browser.newContext({
      viewport: { width: PANEL_WIDTH * 2 + 32 + 80, height: 1000 },
      deviceScaleFactor: 2,
    })
    const p = await ctx.newPage()
    await p.setContent(page(before, after, pair.title), { waitUntil: 'load' })
    const target = join(OUT, `${pair.name}-${viewport}.png`)
    await p.screenshot({ path: target, fullPage: true })
    await ctx.close()
    console.log(`  ${pair.name}-${viewport}.png`)
  }
}

await browser.close()
console.log(`\nWrote ${PAIRS.length * VIEWPORTS.length} pairs to ${OUT}`)
