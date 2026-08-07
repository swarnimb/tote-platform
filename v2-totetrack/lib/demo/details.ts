'use client'

/**
 * DEMO ONLY — client-side row selection for the static export.
 *
 * The four master/detail screens (customers, leads, orders, support) resolve
 * their right-hand pane on the server from `?id=`. A static export has no
 * request, so `searchParams` is always empty at build time: every one of those
 * panes would prerender as "Select a … to view details" and clicking a row
 * would appear to do nothing.
 *
 * In demo mode the page instead prefetches the detail for every row and hands
 * it down as a lookup; this hook picks the right one from the live query
 * string in the browser. Outside demo mode `demoDetails` is undefined and the
 * server-resolved values pass straight through unchanged.
 */

import { useSearchParams } from 'next/navigation'

export type DemoDetails<T> = Record<string, T>

export function useDemoDetail<T>(
  demoDetails: DemoDetails<T> | undefined,
  serverSelectedId: string | null,
  serverDetail: T | null,
): { selectedId: string | null; detail: T | null } {
  // Called unconditionally to satisfy the rules of hooks; the result is only
  // consulted in demo mode. Pages using this wrap the layout in <Suspense>,
  // which a static export requires around any useSearchParams() call.
  const params = useSearchParams()

  if (!demoDetails) {
    return { selectedId: serverSelectedId, detail: serverDetail }
  }

  const id = params.get('id')
  const detail = id ? (demoDetails[id] ?? null) : null
  // An id with no matching row reads as no selection, matching the server's
  // behaviour for a stale or deleted id.
  return { selectedId: detail ? id : null, detail }
}
