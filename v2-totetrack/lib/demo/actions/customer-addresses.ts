/**
 * DEMO ONLY — replaces `lib/actions/customer-addresses.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export async function addCustomerAddress(
  _customer_id: string,
  _address: string,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function updateCustomerAddress(
  _id: string,
  _address: string,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}

export async function deleteCustomerAddress(
  _id: string,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}
