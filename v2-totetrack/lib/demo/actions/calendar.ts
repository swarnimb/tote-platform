/**
 * DEMO ONLY — replaces `lib/actions/calendar.ts` in the static export.
 * See lib/demo/readonly.ts. Signatures mirror the real module so the
 * calling components need no changes.
 */
import { readOnly } from '../readonly'

type Ok = { success: true }
type Err = { error: string }

export async function setProductionPlacement(
  _id: string,
  _input: unknown,
): Promise<Ok | Err> {
  return readOnly()
}

export async function clearProductionPlacement(_id: string): Promise<Ok | Err> {
  return readOnly()
}

export async function toggleSameDayDelivery(_id: string, _next: boolean): Promise<Ok | Err> {
  return readOnly()
}

export async function toggleBackhaul(_id: string, _next: boolean): Promise<Ok | Err> {
  return readOnly()
}
