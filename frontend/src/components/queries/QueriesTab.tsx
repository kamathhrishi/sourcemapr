import { Routes, Route } from 'react-router-dom'
import { QueryList } from './QueryList'
import { QueryDetail } from './QueryDetail'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import type { DashboardData } from '@/api/types'

interface QueriesTabProps {
  data: DashboardData
}

export function QueriesTab({ data }: QueriesTabProps) {
  return (
    <ErrorBoundary>
      <Routes>
        <Route index element={<QueryList data={data} />} />
        <Route path=":queryId" element={<QueryDetail data={data} />} />
      </Routes>
    </ErrorBoundary>
  )
}
