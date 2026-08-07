/**
 * DEMO ONLY — replaces `lib/actions/auth.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

// The demo has no session to establish — the app layout is already
// unauthenticated in demo mode, so sign-in is a no-op success.
export async function signIn(_password: string): Promise<{ error: string | null }> {
  return { error: null }
}

export async function signOut(): Promise<{ error: string } | void> {
  return readOnly()
}
