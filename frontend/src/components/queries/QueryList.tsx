import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronLeft, ChevronRight, Clock, Layers, Cpu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/store'
import { formatLatency, formatTime } from '@/lib/utils'
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
    if (!data?.retrievals || !Array.isArray(data.retrievals)) {
      return []
    }
    const llmCalls = data.llm_calls || []
    return data.retrievals.map((r) => {
      const llmCall = llmCalls.find((l) => l.trace_id === r.trace_id)
      return {
        ...r,
        llmCall,
      }
    }).sort((a, b) => {
      try {
        const aTime = new Date(a.timestamp).getTime()
        const bTime = new Date(b.timestamp).getTime()
        if (isNaN(aTime) || isNaN(bTime)) return 0
        return bTime - aTime
      } catch {
        return 0
      }
    })
  }, [data?.retrievals, data?.llm_calls])

  // Filter
  const filteredQueries = useMemo(() => {
    if (!Array.isArray(queries)) return []
    if (!searchTerm) return queries
    const term = searchTerm.toLowerCase()
    return queries.filter((q) => {
      try {
        return q?.query?.toLowerCase().includes(term) ?? false
      } catch {
        return false
      }
    })
  }, [queries, searchTerm])

  // Paginate
  const totalPages = Math.ceil((filteredQueries?.length || 0) / PAGE_SIZE)
  const paginatedQueries = (filteredQueries || []).slice(
    (queriesPage - 1) * PAGE_SIZE,
    queriesPage * PAGE_SIZE
  )

  const handleQueryClick = (queryId: number) => {
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
    navigate(`${basePath}/queries/${queryId}`)
  }

  const getLatencyColor = (ms: number) => {
    if (ms < 500) return 'var(--success)'
    if (ms < 2000) return 'var(--warning)'
    return 'var(--error)'
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
            <Search className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Queries
            </span>
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ background: 'var(--background-subtle)', color: 'var(--text-muted)' }}
            >
              {queries?.length || 0}
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
                setQueriesPage(1)
              }}
              className="pl-8 h-7 w-48 text-xs"
              style={{ background: 'var(--background)', borderColor: 'var(--border)' }}
            />
          </div>
        </div>

        {/* Table */}
        {paginatedQueries && paginatedQueries.length > 0 ? (
          <>
            <table className="w-full">
              <thead>
                <tr style={{ background: 'var(--background-subtle)' }}>
                  <th
                    className="text-left px-4 py-2 text-[11px] font-medium uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Query
                  </th>
                  <th
                    className="text-center px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-20"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Chunks
                  </th>
                  <th
                    className="text-left px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-32"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Model
                  </th>
                  <th
                    className="text-right px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-24"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Latency
                  </th>
                  <th
                    className="text-right px-4 py-2 text-[11px] font-medium uppercase tracking-wider w-24"
                    style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}
                  >
                    Time
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedQueries.map((query, idx) => (
                  <tr
                    key={query.id}
                    className="cursor-pointer transition-colors"
                    style={{
                      borderBottom: idx < (paginatedQueries?.length || 0) - 1 ? '1px solid var(--border)' : 'none',
                    }}
                    onClick={() => handleQueryClick(query.id)}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded flex items-center justify-center shrink-0"
                          style={{ background: 'var(--background-subtle)' }}
                        >
                          <Search className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                        </div>
                        <span
                          className="text-sm truncate max-w-md"
                          style={{ color: 'var(--text-primary)' }}
                        >
                          {query.query}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--background-subtle)', color: 'var(--text-secondary)' }}
                      >
                        <Layers className="w-3 h-3" />
                        {query.num_results}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {query.llmCall ? (
                        <div className="flex items-center gap-1.5">
                          <Cpu className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
                          <span className="text-xs mono" style={{ color: 'var(--text-secondary)' }}>
                            {query.llmCall.model}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className="text-xs mono font-medium"
                        style={{ color: getLatencyColor(query.duration_ms) }}
                      >
                        {formatLatency(query.duration_ms)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Clock className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                        <span className="text-xs mono" style={{ color: 'var(--text-muted)' }}>
                          {formatTime(query.timestamp)}
                        </span>
                      </div>
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
                  {(queriesPage - 1) * PAGE_SIZE + 1}–{Math.min(queriesPage * PAGE_SIZE, filteredQueries?.length || 0)} of {filteredQueries?.length || 0}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setQueriesPage(queriesPage - 1)}
                    disabled={queriesPage === 1}
                    className="h-7 w-7"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </Button>
                  <span className="text-xs px-2" style={{ color: 'var(--text-secondary)' }}>
                    {queriesPage} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setQueriesPage(queriesPage + 1)}
                    disabled={queriesPage === totalPages}
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
              <Search className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
            </div>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {searchTerm ? 'No queries match your search' : 'No queries yet'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
