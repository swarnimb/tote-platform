/**
 * DEMO ONLY — replaces `lib/actions/invoices.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export type { CreateInvoiceInput } from '@/lib/actions/invoices'

export async function createInvoice(
  _input: unknown,
): Promise<{ id: string; invoiceNumber: string } | { error: string }> {
  return readOnly()
}
