import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
    <div className="h-full overflow-auto p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Documents ({documents.length})
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-apple-secondary" />
              <Input
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setDocsPage(1)
                }}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {paginatedDocs.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead className="w-24 text-right">Pages</TableHead>
                    <TableHead className="w-24 text-right">Chunks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedDocs.map((doc) => (
                    <TableRow
                      key={doc.doc_id}
                      className="cursor-pointer"
                      onClick={() => handleDocClick(doc.doc_id)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-apple-secondary" />
                          <span className="font-medium">{doc.filename}</span>
                        </div>
                        <div className="text-xs text-apple-secondary mt-0.5 truncate max-w-md">
                          {doc.file_path}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {doc.num_pages ?? '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {getChunkCount(doc.doc_id)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-apple-border">
                  <div className="text-sm text-apple-secondary">
                    Showing {(docsPage - 1) * PAGE_SIZE + 1}-
                    {Math.min(docsPage * PAGE_SIZE, filteredDocs.length)} of{' '}
                    {filteredDocs.length}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setDocsPage(docsPage - 1)}
                      disabled={docsPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm">
                      Page {docsPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setDocsPage(docsPage + 1)}
                      disabled={docsPage === totalPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto mb-4 text-apple-secondary" />
              <p className="text-apple-secondary">
                {searchTerm ? 'No documents match your search' : 'No documents yet'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
