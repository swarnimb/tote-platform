/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [],
  },
}

// DEMO ONLY. When NEXT_PUBLIC_DEMO_MODE is unset — which is always the case
// in the production ToteTrack repo — this block is inert and the config above
// is byte-identical to the original.
//
// With it set, the app is compiled to a static export for GitHub Pages:
// every page is prerendered at build time against a locally seeded Postgres,
// so the published HTML carries real (synthetic) data with no database or
// Supabase project behind it at runtime.
if (process.env.NEXT_PUBLIC_DEMO_MODE === 'true') {
  nextConfig.output = 'export'
  // GitHub Pages cannot run the Next.js image optimizer.
  nextConfig.images = { unoptimized: true, remotePatterns: [] }
  // The demo is served from https://<user>.github.io/tote-platform/.
  nextConfig.basePath = '/tote-platform'
  // Emits out/<route>/index.html so Pages resolves directory URLs.
  nextConfig.trailingSlash = true

  // A static export cannot contain Server Actions. Every `'use server'`
  // module the UI imports is swapped for a read-only shim in
  // lib/demo/actions/ that returns the same `{ error }` shape the real
  // actions use for failures. Exact-match aliases (trailing `$`) so the
  // sibling `*.constants` and `*.validation` modules are untouched.
  const path = require('path')
  const SHIMMED = [
    'auth',
    'calendar',
    'customer-addresses',
    'customers',
    'invoices',
    'leads',
    'orders',
    'orders.revert',
    'support',
  ]

  // Matched against the raw import request, before resolution — that is the
  // hook where rewriting `resource.request` actually takes effect. Every UI
  // import of an action module goes through the `@/` alias, so this catches
  // all of them. The `$` anchor keeps the sibling `*.constants` and
  // `*.validation` modules (which are not Server Actions) untouched.
  const SHIM_RE = new RegExp(
    `^@/lib/actions/(${SHIMMED.map((n) => n.replace('.', '\\.')).join('|')})$`,
  )

  nextConfig.webpack = (config, { webpack }) => {
    config.plugins.push(
      new webpack.NormalModuleReplacementPlugin(SHIM_RE, (resource) => {
        const name = resource.request.slice('@/lib/actions/'.length)
        resource.request = path.resolve(__dirname, `lib/demo/actions/${name}.ts`)
      }),
      // Prerendering happens with no request and no session cookie, so the
      // real cookie-reading Supabase client would send every page to /login.
      new webpack.NormalModuleReplacementPlugin(
        /^@\/lib\/supabase\/server$/,
        (resource) => {
          resource.request = path.resolve(__dirname, 'lib/demo/supabase-server.ts')
        },
      ),
    )
    return config
  }
}

module.exports = nextConfig
