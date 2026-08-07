import {
  getTickets,
  getTicketDetail,
  type TicketDetail as TicketDetailType,
} from '@/db/queries/support'
import { TicketNotFoundError } from '@/lib/errors'
import { isUuid } from '@/lib/validators/uuid'
import SupportLayout from '@/components/support/SupportLayout'
import PageTransition from '@/components/shell/PageTransition'
import { Suspense } from 'react'
import { IS_DEMO } from '@/lib/demo/flag'

interface SupportPageProps {
  searchParams: {
    id?: string
  }
}

async function loadTicketDetail(ticketId: string): Promise<TicketDetailType | null> {
  try {
    return await getTicketDetail(ticketId)
  } catch (error) {
    // Stale or deleted id is not a server error — surface as "no selection".
    // Other errors (DatabaseError) bubble to the Next.js error boundary.
    if (error instanceof TicketNotFoundError) return null
    throw error
  }
}

/**
 * Support route. Validates `id` from searchParams as a UUID, then fetches
 * the ticket list and (when selected) the detail + attachments in parallel
 * so the screen renders on a single server round-trip. Auth is enforced
 * by the surrounding `app/(app)/layout.tsx` guard.
 */
export default async function SupportPage({ searchParams }: SupportPageProps) {
  const selectedId = isUuid(searchParams.id) ? searchParams.id : null

  const [tickets, detail] = await Promise.all([
    getTickets(),
    selectedId ? loadTicketDetail(selectedId) : Promise.resolve(null),
  ])

  const demoDetails = IS_DEMO ? await loadAllDetailsForDemo(tickets.map((t) => t.id)) : undefined

  const layout = (
    <SupportLayout
      tickets={tickets}
      selectedId={selectedId}
      detail={detail}
      demoDetails={demoDetails}
    />
  )

  return (
    <PageTransition>
      {/* A static export requires a Suspense boundary around the
          useSearchParams() call the demo selection hook makes. */}
      {IS_DEMO ? <Suspense fallback={null}>{layout}</Suspense> : layout}
    </PageTransition>
  )
}

/**
 * DEMO ONLY — the static export cannot resolve `?id=` on the server, so every
 * row's detail is prerendered into the page and picked client-side.
 */
async function loadAllDetailsForDemo(ids: string[]): Promise<Record<string, TicketDetailType>> {
  const entries = await Promise.all(
    ids.map(async (id) => {
      const detail = await loadTicketDetail(id)
      return detail ? ([id, detail] as const) : null
    }),
  )
  return Object.fromEntries(entries.filter(Boolean) as Array<readonly [string, TicketDetailType]>)
}
