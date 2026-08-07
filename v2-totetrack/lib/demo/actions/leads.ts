/**
 * DEMO ONLY — replaces `lib/actions/leads.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

export type { NextActionInput, LeadInput } from '@/lib/actions/leads'

export async function addLeadNote(
  _leadId: string,
  _content: string,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function setNextAction(
  _leadId: string,
  _data: unknown,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}

export async function createLead(
  _input: unknown,
): Promise<{ id: string } | { error: string }> {
  return readOnly()
}

export async function updateLead(
  _id: string,
  _input: unknown,
): Promise<{ success: true } | { error: string }> {
  return readOnly()
}

export async function convertLeadToCustomer(
  _leadId: string,
  _force = false,
): Promise<{ customerId: string } | { warning: string } | { error: string }> {
  return readOnly()
}
