import { Routes, Route } from 'react-router-dom'
import { EvaluationsList } from './EvaluationsList'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import type { DashboardData } from '@/api/types'

interface EvaluationsTabProps {
  data: DashboardData
}

export function EvaluationsTab({ data }: EvaluationsTabProps) {
  return (
    <ErrorBoundary>
      <Routes>
        <Route index element={<EvaluationsList data={data} />} />
      </Routes>
    </ErrorBoundary>
  )
}
