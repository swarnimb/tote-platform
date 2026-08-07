/**
 * DEMO ONLY — not part of the production ToteTrack application.
 *
 * The published demo is a static export with no database behind it, so every
 * mutation is refused. Each server action under `lib/actions/` is swapped for
 * a shim in `lib/demo/actions/` at build time (see the webpack replacement in
 * `next.config.js`, active only when NEXT_PUBLIC_DEMO_MODE=true).
 *
 * The shims return the same `{ error }` shape the real actions use for
 * failures, so the existing toast and error handling in each component
 * surfaces this message without any component-level changes.
 */

export const DEMO_READONLY_MESSAGE =
  'This is a read-only demo — changes are not saved.'

/** The failure shape every shimmed action returns. */
export function readOnly(): { error: string } {
  return { error: DEMO_READONLY_MESSAGE }
}
