import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import AppShell from '@/components/shell/AppShell'
import ToastProvider from '@/components/shell/ToastProvider'

// Every authenticated route reads session cookies via `createClient()` —
// these can only be resolved per-request, so opt out of static prerender.
// DEMO ONLY: the static export has no request to resolve and no session to
// read, so it prerenders instead. NEXT_PUBLIC_DEMO_MODE is never set in the
// production repo, where this evaluates to 'force-dynamic' as before.
export const dynamic =
  process.env.NEXT_PUBLIC_DEMO_MODE === 'true' ? 'force-static' : 'force-dynamic'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <ToastProvider>
      <AppShell>{children}</AppShell>
    </ToastProvider>
  )
}
