/**
 * DEMO ONLY — writes the static export's landing page.
 *
 * `app/page.tsx` calls `redirect('/dashboard')`, which a static export cannot
 * express: there is no server to issue the 307, and the generated index.html
 * carries no meta refresh, so the site root would sit blank until the client
 * bundle booted. This replaces it with a plain meta-refresh page that also
 * works with JavaScript disabled.
 *
 * Run after `next build` in demo mode.
 */

import { writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'out', 'index.html')
const TARGET = './dashboard/'

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="refresh" content="0; url=${TARGET}" />
    <link rel="canonical" href="${TARGET}" />
    <title>ToteTrack — demo</title>
    <style>
      body {
        margin: 0; min-height: 100vh; display: grid; place-items: center;
        background: #f0f3f7; color: #334155;
        font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
      }
      a { color: #007a8a; }
    </style>
  </head>
  <body>
    <p>Loading the ToteTrack demo… <a href="${TARGET}">Continue</a></p>
    <script>location.replace('${TARGET}')</script>
  </body>
</html>
`

await writeFile(OUT, html, 'utf8')
console.log(`[write-root-redirect] ${OUT} -> ${TARGET}`)
