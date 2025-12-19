import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronLeft, ChevronRight, Clock, Layers, Cpu } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAppStore } from '@/store'
import { formatLatency, formatTime, getLatencyColor } from '@/lib/utils'
import type { DashboardData } from '@/api/types'

interface QueryListProps {
  data: DashboardData
}

const PAGE_SIZE = 20

export function QueryList({ data }: QueryListProps) {
  const navigate = useNavigate()
  const { currentExperimentId, queriesPage, setQueriesPage } = useAppStore()
  const [searchTerm, setSearchTerm] = useState('')

  // Combine retrievals with LLM calls to show queries
  const queries = useMemo(() => {
    return data.retrievals.map((r) => {
      const llmCall = data.llm_calls.find((l) => l.trace_id === r.trace_id)
      return {
        ...r,
        llmCall,
      }
    }).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  }, [data.retrievals, data.llm_calls])

  // Filter
  const filteredQueries = useMemo(() => {
    if (!searchTerm) return queries
    const term = searchTerm.toLowerCase()
    return queries.filter((q) => q.query.toLowerCase().includes(term))
  }, [queries, searchTerm])

  // Paginate
  const totalPages = Math.ceil(filteredQueries.length / PAGE_SIZE)
  const paginatedQueries = filteredQueries.slice(
    (queriesPage - 1) * PAGE_SIZE,
    queriesPage * PAGE_SIZE
  )

  const handleQueryClick = (queryId: number) => {
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
    navigate(`${basePath}/queries/${queryId}`)
  }

  return (
    <div className="h-full overflow-auto p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Search className="w-4 h-4" />
              Queries ({queries.length})
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-apple-secondary" />
              <Input
                placeholder="Search queries..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setQueriesPage(1)
                }}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {paginatedQueries.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Query</TableHead>
                    <TableHead className="w-24 text-center">Chunks</TableHead>
                    <TableHead className="w-32">Model</TableHead>
                    <TableHead className="w-28 text-right">Latency</TableHead>
                    <TableHead className="w-24 text-right">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedQueries.map((query) => (
                    <TableRow
                      key={query.id}
                      className="cursor-pointer"
                      onClick={() => handleQueryClick(query.id)}
                    >
                      <TableCell>
                        <div className="max-w-md truncate font-medium">
                          {query.query}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="secondary" className="gap-1">
                          <Layers className="w-3 h-3" />
                          {query.num_results}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {query.llmCall ? (
                          <div className="flex items-center gap-1.5">
                            <Cpu className="w-3 h-3 text-apple-secondary" />
                            <span className="text-sm">{query.llmCall.model}</span>
                          </div>
                        ) : (
                          <span className="text-apple-secondary text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className={`text-sm ${getLatencyColor(query.duration_ms)}`}>
                            {formatLatency(query.duration_ms)}
                          </span>
                          <div className="w-16 h-1.5 bg-apple-tertiary rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                query.duration_ms < 500
                                  ? 'bg-apple-green'
                                  : query.duration_ms < 2000
                                  ? 'bg-apple-orange'
                                  : 'bg-apple-red'
                              }`}
                              style={{
                                width: `${Math.min(100, (query.duration_ms / 5000) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1 text-apple-secondary">
                          <Clock className="w-3 h-3" />
                          <span className="text-xs">{formatTime(query.timestamp)}</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-apple-border">
                  <div className="text-sm text-apple-secondary">
                    Showing {(queriesPage - 1) * PAGE_SIZE + 1}-
                    {Math.min(queriesPage * PAGE_SIZE, filteredQueries.length)} of{' '}
                    {filteredQueries.length}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setQueriesPage(queriesPage - 1)}
                      disabled={queriesPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm">
                      Page {queriesPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setQueriesPage(queriesPage + 1)}
                      disabled={queriesPage === totalPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Search className="w-12 h-12 mx-auto mb-4 text-apple-secondary" />
              <p className="text-apple-secondary">
                {searchTerm ? 'No queries match your search' : 'No queries yet'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
