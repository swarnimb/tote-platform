/**
 * DEMO ONLY — captures every ToteTrack screen for the v2 (after) asset set.
 *
 * Point it at the built static export (served locally, or the live GitHub
 * Pages URL) and it walks every route at both viewport widths.
 *
 * Usage:
 *   node screenshot_demo.mjs                          # http://127.0.0.1:8022/tote-platform
 *   DEMO_BASE_URL=https://... node screenshot_demo.mjs
 */

import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const BASE_URL = process.env.DEMO_BASE_URL ?? 'http://127.0.0.1:8022/tote-platform'
const OUT_ROOT = join(HERE, '..', 'assets', 'v2-totetrack')

// Matches the widths used for the v1 capture so the before/after pairs line up.
const VIEWPORTS = { 'desktop-1280': 1280, 'ipad-768': 768 }

// `select` names screens whose right-hand pane only fills once a row is
// chosen. Capturing them untouched ships a screenshot of an empty state.
const ROUTES = [
  ['00-login', '/login/'],
  ['01-dashboard', '/dashboard/'],
  ['02-customers', '/customers/', { select: 'Select a customer to view details.' }],
  ['03-orders', '/orders/', { select: 'Select an order to view details.' }],
  ['04-leads', '/leads/', { select: 'Select a lead to view details.' }],
  ['05-invoices', '/invoices/'],
  ['06-calendar', '/calendar/'],
  // Support's right pane defaults to the new-ticket form rather than an empty
  // state, so it is never blank — but the ticket detail is the better shot.
  ['07-support', '/support/', { select: 'Select an issue to view details.' }],
]

/**
 * Clicks the first row of a master/detail screen and verifies the detail pane
 * actually filled. Throws rather than shipping a screenshot of an empty state.
 */
async function selectFirstRow(page, emptyStateText) {
  // Customers, leads and tickets render rows as buttons in a list; orders
  // render them as clickable table rows.
  const row = page.locator('ul li button, ul li a, tbody tr[tabindex]').first()
  if (!(await row.count())) throw new Error('no selectable rows found')
  await row.click()
  await page.waitForTimeout(1500)
  if (await page.getByText(emptyStateText, { exact: false }).count()) {
    throw new Error(`detail pane still empty after selecting a row (${emptyStateText})`)
  }
}

// The dashboard's revenue chart ships collapsed. Screenshotting it as-is
// leaves an empty card where the twelve-month trend should be.
async function expandRevenueChart(page) {
  const toggle = page.locator('button[aria-controls="revenue-chart-body"]')
  if ((await toggle.count()) && (await toggle.getAttribute('aria-expanded')) === 'false') {
    await toggle.click()
    // The collapse transition, then Recharts' own entrance animation, then a
    // margin — the series paints last and a short wait catches an empty plot.
    await page.waitForTimeout(3000)
  }
}

async function capture(page, label, path, outDir, afterLoad) {
  const resp = await page.goto(`${BASE_URL}${path}`, { waitUntil: 'networkidle' })
  if (!resp || resp.status() >= 400) {
    throw new Error(`${path} returned ${resp ? resp.status() : 'no response'} — refusing to ship a broken screenshot`)
  }
  // Framer Motion entrance animations and Recharts both settle after paint.
  await page.waitForTimeout(1600)
  if (afterLoad) await afterLoad(page)

  // `fullPage: true` resizes the viewport at capture time, which makes
  // Recharts' ResponsiveContainer re-measure and replay its entrance
  // animation — the screenshot then lands on an empty plot area. Resizing
  // first, settling, and then capturing the (now fully visible) viewport
  // avoids the race without touching the app's animation code.
  const height = await page.evaluate(() => document.body.scrollHeight)
  await page.setViewportSize({ width: page.viewportSize().width, height })
  await page.waitForTimeout(1800)

  const target = join(outDir, `${label}.png`)
  await page.screenshot({ path: target })
  await page.setViewportSize({ width: page.viewportSize().width, height: 1000 })
  console.log(`  ${label}.png`)
}

const browser = await chromium.launch()
const consoleErrors = []

for (const [vpName, width] of Object.entries(VIEWPORTS)) {
  const outDir = join(OUT_ROOT, vpName)
  await mkdir(outDir, { recursive: true })
  console.log(`\n${vpName}:`)

  const ctx = await browser.newContext({
    viewport: { width, height: 1000 },
    deviceScaleFactor: 2,
  })
  const page = await ctx.newPage()
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(`[${vpName}] ${msg.text()}`)
  })

  for (const [label, path, opts] of ROUTES) {
    let hook
    if (label === '01-dashboard') hook = expandRevenueChart
    else if (opts?.select) hook = (p) => selectFirstRow(p, opts.select)
    await capture(page, label, path, outDir, hook)
  }
  await ctx.close()
}

await browser.close()

console.log(`\nWrote screenshots to ${OUT_ROOT}`)

// A demo that logs errors in the console is not shippable — surface them.
if (consoleErrors.length) {
  console.error(`\n${consoleErrors.length} console error(s):`)
  for (const e of [...new Set(consoleErrors)]) console.error(`  ${e}`)
  process.exit(1)
}
console.log('No console errors.')
