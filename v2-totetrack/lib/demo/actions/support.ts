/**
 * DEMO ONLY — replaces `lib/actions/support.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export type { CreateTicketInput } from '@/lib/actions/support'

export async function createTicket(
  _input: unknown,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function uploadTicketAttachment(
  _ticketId: string,
  _file: File,
): Promise<{ path: string } | { error: string }> {
  return readOnly()
}

export async function getSupportAttachmentSignedUrl(
  _attachmentId: string,
): Promise<{ url: string } | { error: string }> {
  return readOnly()
}
