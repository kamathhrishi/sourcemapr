import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/store'
import type { DashboardData } from '@/api/types'

interface DocumentListProps {
  data: DashboardData
}

const PAGE_SIZE = 20

export function DocumentList({ data }: DocumentListProps) {
  const navigate = useNavigate()
  const { currentExperimentId, docsPage, setDocsPage } = useAppStore()
  const [searchTerm, setSearchTerm] = useState('')

  const documents = useMemo(() => {
    return Object.values(data.documents)
  }, [data.documents])

  const chunks = useMemo(() => {
    return Object.values(data.chunks)
  }, [data.chunks])

  // Filter documents
  const filteredDocs = useMemo(() => {
    if (!searchTerm) return documents
    const term = searchTerm.toLowerCase()
    return documents.filter(
      (doc) =>
        doc.filename.toLowerCase().includes(term) ||
        doc.file_path.toLowerCase().includes(term)
    )
  }, [documents, searchTerm])

  // Paginate
  const totalPages = Math.ceil(filteredDocs.length / PAGE_SIZE)
  const paginatedDocs = filteredDocs.slice(
    (docsPage - 1) * PAGE_SIZE,
    docsPage * PAGE_SIZE
  )

  // Get chunk count for each document
  const getChunkCount = (docId: string) => {
    return chunks.filter((c) => c.doc_id === docId).length
  }

  const handleDocClick = (docId: string) => {
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
    navigate(`${basePath}/documents/${encodeURIComponent(docId)}`)
  }

  return (
    <div className="h-full overflow-auto p-6" style={{ background: 'var(--background)' }}>
      <div className="console-card">
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Documents
            </span>
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ background: 'var(--background-subtle)', color: 'var(--text-muted)' }}
            >
              {documents.length}
            </span>
          </div>
          <div className="relative">
            <Search
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5"
              style={{ color: 'var(--text-muted)' }}
            />
            <Input
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setDocsPage(1)
              }}
              className="pl-8 h-7 w-48 text-xs"
              style={{ background: 'var(--background)', borderColor: 'var(--border)' }}
            />
          </div>
        </div>

        {/* Table */}
        {paginatedDocs.length > 0 ? (
          <>
            <table className="w-full">
              <thead>
                <tr style={{ background: 'var(--background-subtle)' }}>
                  <th
                    className="text-left px-4 py-2 text-[11px] font-medium uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Filename
                  </th>
                  <th
                    className="text-right px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-20"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Pages
                  </th>
                  <th
                    className="text-right px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-20"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Chunks
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedDocs.map((doc, idx) => (
                  <tr
                    key={doc.doc_id}
                    className="cursor-pointer transition-colors"
                    style={{
                      borderBottom: idx < paginatedDocs.length - 1 ? '1px solid var(--border)' : 'none',
                    }}
                    onClick={() => handleDocClick(doc.doc_id)}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded flex items-center justify-center shrink-0"
                          style={{ background: 'var(--background-subtle)' }}
                        >
                          <FileText className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                            {doc.filename}
                          </div>
                          <div className="text-xs truncate max-w-md mono" style={{ color: 'var(--text-muted)' }}>
                            {doc.file_path}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm mono" style={{ color: 'var(--text-secondary)' }}>
                        {doc.num_pages ?? '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className="text-xs px-1.5 py-0.5 rounded mono"
                        style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}
                      >
                        {getChunkCount(doc.doc_id)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div
                className="flex items-center justify-between px-4 py-3"
                style={{ borderTop: '1px solid var(--border)' }}
              >
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {(docsPage - 1) * PAGE_SIZE + 1}–{Math.min(docsPage * PAGE_SIZE, filteredDocs.length)} of {filteredDocs.length}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setDocsPage(docsPage - 1)}
                    disabled={docsPage === 1}
                    className="h-7 w-7"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </Button>
                  <span className="text-xs px-2" style={{ color: 'var(--text-secondary)' }}>
                    {docsPage} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setDocsPage(docsPage + 1)}
                    disabled={docsPage === totalPages}
                    className="h-7 w-7"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="py-12 text-center">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center mx-auto mb-3"
              style={{ background: 'var(--background-subtle)' }}
            >
              <FileText className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
            </div>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {searchTerm ? 'No documents match your search' : 'No documents yet'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
