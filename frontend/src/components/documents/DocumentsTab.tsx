import { Routes, Route } from 'react-router-dom'
import { DocumentList } from './DocumentList'
import { DocumentViewer } from './DocumentViewer'
import type { DashboardData } from '@/api/types'

interface DocumentsTabProps {
  data: DashboardData
}

export function DocumentsTab({ data }: DocumentsTabProps) {
  return (
    <Routes>
      <Route index element={<DocumentList data={data} />} />
      <Route path=":docId" element={<DocumentViewer data={data} />} />
    </Routes>
  )
}
