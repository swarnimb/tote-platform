/**
 * DEMO ONLY — replaces `lib/supabase/server.ts` in the static export.
 *
 * The published demo has no Supabase project behind it. Pages are prerendered
 * at build time, where there is no request and therefore no session cookie to
 * read. This stub reports a signed-in user so the auth guards in
 * `app/(app)/layout.tsx` and `app/(auth)/login/page.tsx` pass during the
 * export instead of redirecting to /login.
 *
 * It grants nothing: every write is already refused by the action shims in
 * lib/demo/actions/, and the exported HTML has no database connection at all.
 */

const DEMO_USER = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'demo@totetrack.app',
}

export function createClient() {
  return {
    auth: {
      async getUser() {
        return { data: { user: DEMO_USER }, error: null }
      },
      async signInWithPassword() {
        return { data: { user: DEMO_USER, session: null }, error: null }
      },
      async signOut() {
        return { error: null }
      },
    },
  } as never
}
