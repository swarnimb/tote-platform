/**
 * DEMO ONLY — replaces `lib/actions/orders.revert.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export async function revertOrderToScheduled(
  _id: string,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}
