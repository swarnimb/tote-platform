/**
 * DEMO ONLY — prepares a plain PostgreSQL database for the static demo build.
 *
 * The production schema targets Supabase, so two of the thirteen migrations
 * assume Supabase-managed objects that a bare Postgres does not have:
 *
 *   0002_rls_policies.sql        GRANTs to the `authenticated` role
 *   0003_storage_buckets.sql     INSERTs into `storage.buckets`
 *   0012_customer_addresses.sql  also GRANTs to `authenticated`
 *
 * Rather than fork the migrations, this creates the missing roles and a
 * minimal `auth` schema first, then applies every migration in order. The
 * storage migration is skipped outright — the demo has no file uploads, and
 * recreating Supabase's storage schema to insert one bucket row buys nothing.
 *
 * Usage:  node db/demo/setup-db.mjs            (reads DATABASE_URL)
 */

import postgres from 'postgres'
import { readdir, readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const MIGRATIONS_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'migrations')

// Depends on Supabase Storage, which the demo never touches.
const SKIP = new Set(['0003_storage_buckets.sql'])

const SUPABASE_SHIMS = `
  DO $$ BEGIN
    CREATE ROLE authenticated NOLOGIN;
  EXCEPTION WHEN duplicate_object THEN NULL; END $$;
  DO $$ BEGIN
    CREATE ROLE anon NOLOGIN;
  EXCEPTION WHEN duplicate_object THEN NULL; END $$;
  DO $$ BEGIN
    CREATE ROLE service_role NOLOGIN;
  EXCEPTION WHEN duplicate_object THEN NULL; END $$;

  CREATE SCHEMA IF NOT EXISTS auth;

  -- RLS policies call these. A fixed uid is correct here: the demo has exactly
  -- one notional user and the exported HTML has no database behind it anyway.
  CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE AS $fn$ SELECT '00000000-0000-0000-0000-000000000001'::uuid $fn$;
  CREATE OR REPLACE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE AS $fn$ SELECT 'authenticated'::text $fn$;
`

const url = process.env.DATABASE_URL
if (!url) {
  console.error('[setup-db] DATABASE_URL is not set.')
  process.exit(1)
}

const sql = postgres(url, { prepare: false, max: 1 })

try {
  console.log('[setup-db] Creating Supabase-compatible roles and auth schema...')
  await sql.unsafe(SUPABASE_SHIMS)

  const files = (await readdir(MIGRATIONS_DIR))
    .filter((f) => f.endsWith('.sql'))
    .sort()

  for (const file of files) {
    if (SKIP.has(file)) {
      console.log(`  skip  ${file}  (Supabase Storage — not used by the demo)`)
      continue
    }
    const body = await readFile(join(MIGRATIONS_DIR, file), 'utf8')
    await sql.unsafe(body)
    console.log(`  ok    ${file}`)
  }

  console.log('[setup-db] Schema ready.')
} catch (cause) {
  console.error('[setup-db] Failed:', cause)
  process.exit(1)
} finally {
  await sql.end()
}
