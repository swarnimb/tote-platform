'use client'

import { useCallback, useState } from 'react'
import { useRouter } from 'next/navigation'
import LeadList from './LeadList'
import LeadDetail, { LeadDetailEmptyState } from './LeadDetail'
import LeadForm from './LeadForm'
import ConvertLeadDialog from './ConvertLeadDialog'
import DetailDrawer from '@/components/shell/DetailDrawer'
import { useDemoDetail, type DemoDetails } from '@/lib/demo/details'
import type { LeadDetail as LeadDetailType, LeadListRow, LeadListStatus, LeadNote } from '@/db/queries/leads'

export type LeadLayoutInitialMode = 'detail' | 'new-lead'

/** DEMO ONLY — see lib/demo/details.ts. Undefined outside the static demo. */
export interface LeadDemoBundle {
  detail: LeadDetailType
  notes: LeadNote[]
}

interface LeadLayoutProps {
  leads: LeadListRow[]
  selectedId: string | null
  status: LeadListStatus
  search: string
  detail: LeadDetailType | null
  notes: LeadNote[]
  initialMode?: LeadLayoutInitialMode
  /** DEMO ONLY — every row's detail, keyed by id, for client-side selection. */
  demoDetails?: DemoDetails<LeadDemoBundle>
}

type RightPanelMode = 'detail' | 'new-lead' | 'edit-lead'

/**
 * Two-panel shell for the Leads screen. Left: filterable/searchable lead list.
 * Right: lead detail, new-lead form, or edit-lead form.
 * ConvertLeadDialog overlays the right panel when conversion is triggered.
 */
export default function LeadLayout({
  leads,
  selectedId: serverSelectedId,
  status,
  search,
  detail: serverDetail,
  notes: serverNotes,
  initialMode = 'detail',
  demoDetails,
}: LeadLayoutProps) {
  const router = useRouter()

  // Outside demo mode this is a pass-through of the server-resolved values.
  const { selectedId, detail: bundle } = useDemoDetail<LeadDemoBundle>(
    demoDetails,
    serverSelectedId,
    serverDetail ? { detail: serverDetail, notes: serverNotes } : null,
  )
  const detail = bundle?.detail ?? null
  const notes = bundle?.notes ?? serverNotes
  const [mode, setMode] = useState<RightPanelMode>(initialMode)
  const [showConvertDialog, setShowConvertDialog] = useState(false)

  const openNew = useCallback(() => setMode('new-lead'), [])
  const openEdit = useCallback(() => setMode('edit-lead'), [])
  const closeForm = useCallback(() => setMode('detail'), [])

  const handleSaved = useCallback(() => {
    setMode('detail')
    router.refresh()
  }, [router])

  const handleConverted = useCallback(() => {
    // ConvertLeadDialog redirects to /customers on success — nothing to clean up here.
    setShowConvertDialog(false)
  }, [])

  const renderRightPanel = () => {
    if (mode === 'new-lead') {
      return <LeadForm mode="create" onClose={closeForm} onSaved={handleSaved} />
    }
    if (mode === 'edit-lead' && detail) {
      return (
        <LeadForm mode="edit" initialDetail={detail} onClose={closeForm} onSaved={handleSaved} />
      )
    }
    if (!detail) return <LeadDetailEmptyState />
    return (
      <LeadDetail
        detail={detail}
        notes={notes}
        onEdit={openEdit}
        onConvert={() => setShowConvertDialog(true)}
      />
    )
  }

  const isDrawerOpen = mode !== 'detail' || !!detail
  const handleDrawerClose = useCallback(() => {
    setMode('detail')
    if (selectedId) router.push('/leads')
  }, [router, selectedId])

  return (
    <div className="h-[calc(100vh-0.75rem)] lg:grid lg:grid-cols-[minmax(320px,38%)_1fr] lg:grid-rows-[minmax(0,1fr)]">
      <LeadList
        leads={leads}
        selectedId={selectedId}
        status={status}
        search={search}
        onNew={openNew}
      />
      <DetailDrawer
        isOpen={isDrawerOpen}
        onClose={handleDrawerClose}
        ariaLabel="Lead detail"
      >
        {renderRightPanel()}
        {detail && (
          <ConvertLeadDialog
            open={showConvertDialog}
            leadId={detail.id}
            leadName={detail.name}
            onCancel={() => setShowConvertDialog(false)}
          />
        )}
      </DetailDrawer>
    </div>
  )
}
