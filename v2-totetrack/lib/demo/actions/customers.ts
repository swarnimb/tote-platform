/**
 * DEMO ONLY — replaces `lib/actions/customers.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export type { CustomerInput } from '@/lib/actions/customers'

export async function createCustomer(
  _input: unknown,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function updateCustomer(
  _id: string,
  _input: unknown,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}

export async function deleteCustomer(
  _id: string,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}
