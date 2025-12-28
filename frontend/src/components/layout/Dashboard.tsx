import { useEffect } from 'react'
import { Routes, Route, useParams, useNavigate, useLocation } from 'react-router-dom'
import { useDashboardData } from '@/hooks/useApi'
import { useAppStore } from '@/store'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { Overview } from '@/components/dashboard/Overview'
import { DocumentsTab } from '@/components/documents/DocumentsTab'
import { QueriesTab } from '@/components/queries/QueriesTab'
import { EvaluationsTab } from '@/components/evaluations/EvaluationsTab'
import { Skeleton } from '@/components/ui/skeleton'

export function Dashboard() {
  const { experimentId } = useParams<{ experimentId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { setExperiment, activeTab, setActiveTab } = useAppStore()

  // Parse experiment ID (could be 'all' or a number)
  const expId = experimentId === 'all' ? null : Number(experimentId)

  // Set experiment in store when route changes
  useEffect(() => {
    setExperiment(expId)
  }, [expId, setExperiment])

  // Sync route with active tab
  useEffect(() => {
    const path = location.pathname
    if (path.includes('/documents')) {
      setActiveTab('documents')
    } else if (path.includes('/queries')) {
      setActiveTab('queries')
    } else if (path.includes('/evaluations')) {
      setActiveTab('evaluations')
    } else {
      setActiveTab('overview')
    }
  }, [location.pathname, setActiveTab])

  const { data, isLoading, error, refetch } = useDashboardData(expId)

  const handleTabChange = (tab: 'overview' | 'documents' | 'queries' | 'evaluations') => {
    setActiveTab(tab)
    const basePath = `/experiment/${experimentId}`
    if (tab === 'overview') {
      navigate(basePath)
    } else {
      navigate(`${basePath}/${tab}`)
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="text-center">
          <p className="text-apple-red text-lg mb-2">Failed to load dashboard data</p>
          <p className="text-apple-secondary">{String(error)}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-apple-bg flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={handleTabChange} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <Header
          experimentId={expId}
          experiments={data?.experiments ?? []}
          framework={data?.experiments?.find((e) => e.id === expId)?.framework ?? null}
          onRefresh={() => refetch()}
        />

        {/* Content */}
        <main className="flex-1 overflow-hidden">
          {isLoading ? (
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Skeleton key={i} className="h-24 rounded-xl" />
                ))}
              </div>
              <Skeleton className="h-64 rounded-xl" />
            </div>
          ) : data ? (
            <Routes>
              <Route index element={<Overview data={data} />} />
              <Route path="documents/*" element={<DocumentsTab data={data} />} />
              <Route path="queries/*" element={<QueriesTab data={data} />} />
              <Route path="evaluations/*" element={<EvaluationsTab data={data} />} />
            </Routes>
          ) : null}
        </main>
      </div>
    </div>
  )
}
