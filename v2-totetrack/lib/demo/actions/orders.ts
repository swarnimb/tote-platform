/**
 * DEMO ONLY — replaces `lib/actions/orders.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export async function createOrder(
  _input: unknown,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function updateOrder(
  _id: string,
  _input: unknown,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}

export async function updateOrderStatus(
  _id: string,
  _newStatus: unknown,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}
