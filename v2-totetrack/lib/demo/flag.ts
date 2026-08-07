/**
 * DEMO ONLY — the single switch every demo-mode branch reads.
 *
 * `NEXT_PUBLIC_DEMO_MODE` is never set in the production repo, so this is
 * `false` there and every guarded branch is dead code the bundler drops.
 */
export const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'
