import { useState, useMemo } from 'react'
import { BarChart3, ChevronLeft, ChevronRight, Search, Bot, Tag, AlertCircle, Star, ChevronDown, ChevronUp, MessageSquare, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/store'
import { formatTime } from '@/lib/utils'
import type { DashboardData, Evaluation } from '@/api/types'

interface EvaluationsListProps {
  data: DashboardData
}

const PAGE_SIZE = 20

const EVAL_TYPE_ICONS: Record<string, typeof Star> = {
  llm_judge: Star,
  category: Tag,
  error_class: AlertCircle,
}

const EVAL_TYPE_LABELS: Record<string, string> = {
  llm_judge: 'LLM Judge',
  category: 'Category',
  error_class: 'Error Class',
}

export function EvaluationsList({ data }: EvaluationsListProps) {
  const { evaluationsPage, setEvaluationsPage } = useAppStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [selectedEval, setSelectedEval] = useState<Evaluation | null>(null)

  // Build a map of retrieval_id -> query text
  const retrievalQueryMap = useMemo(() => {
    const map: Record<string, { query: string; response?: string }> = {}
    if (data?.retrievals) {
      for (const r of data.retrievals) {
        const key = r.retrieval_id || String(r.id)
        map[key] = { query: r.query }
      }
    }
    // Also map LLM calls to get responses
    if (data?.llm_calls) {
      for (const l of data.llm_calls) {
        const entry = l.retrieval_id ? map[l.retrieval_id] : undefined
        if (entry) {
          entry.response = l.response
        }
      }
    }
    return map
  }, [data?.retrievals, data?.llm_calls])

  const evaluations = useMemo(() => {
    if (!data?.evaluations || !Array.isArray(data.evaluations)) {
      return []
    }
    return [...data.evaluations].sort((a, b) => {
      try {
        const aTime = new Date(a.created_at).getTime()
        const bTime = new Date(b.created_at).getTime()
        if (isNaN(aTime) || isNaN(bTime)) return 0
        return bTime - aTime
      } catch {
        return 0
      }
    })
  }, [data?.evaluations])

  // Get unique types for filters
  const evalTypes = useMemo(() => {
    const types = new Set<string>()
    evaluations.forEach((e) => types.add(e.evaluation_type))
    return Array.from(types)
  }, [evaluations])

  // Filter - also search in query text
  const filteredEvaluations = useMemo(() => {
    if (!Array.isArray(evaluations)) return []
    return evaluations.filter((e) => {
      if (typeFilter && e.evaluation_type !== typeFilter) return false
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        const matchesMetric = e.metric_name?.toLowerCase().includes(term) ?? false
        const matchesCategory = e.category?.toLowerCase().includes(term) ?? false
        const matchesAgent = e.agent_name?.toLowerCase().includes(term) ?? false
        const matchesReasoning = e.reasoning?.toLowerCase().includes(term) ?? false
        // Also search in query text
        const queryInfo = e.retrieval_id ? retrievalQueryMap[e.retrieval_id] : null
        const matchesQuery = queryInfo?.query?.toLowerCase().includes(term) ?? false
        return matchesMetric || matchesCategory || matchesAgent || matchesReasoning || matchesQuery
      }
      return true
    })
  }, [evaluations, typeFilter, searchTerm, retrievalQueryMap])

  // Stats
  const stats = useMemo(() => {
    const llmJudge = evaluations.filter((e) => e.evaluation_type === 'llm_judge' && e.score !== null)
    const avgScore = llmJudge.length > 0
      ? llmJudge.reduce((sum, e) => sum + (e.score ?? 0), 0) / llmJudge.length
      : 0
    const passCount = llmJudge.filter(e => (e.score ?? 0) >= 0.7).length
    const failCount = llmJudge.filter(e => (e.score ?? 0) < 0.5).length
    const agents = new Set(evaluations.filter((e) => e.agent_name).map((e) => e.agent_name))
    return {
      total: evaluations.length,
      avgScore,
      passCount,
      failCount,
      agentCount: agents.size,
    }
  }, [evaluations])

  // Paginate
  const totalPages = Math.ceil((filteredEvaluations?.length || 0) / PAGE_SIZE)
  const paginatedEvaluations = (filteredEvaluations || []).slice(
    (evaluationsPage - 1) * PAGE_SIZE,
    evaluationsPage * PAGE_SIZE
  )

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'var(--text-muted)'
    if (score >= 0.7) return 'var(--success)'
    if (score >= 0.5) return 'var(--warning)'
    return 'var(--error)'
  }

  const getScoreBg = (score: number | null) => {
    if (score === null) return 'var(--background-subtle)'
    if (score >= 0.7) return 'rgba(34, 197, 94, 0.1)'
    if (score >= 0.5) return 'rgba(234, 179, 8, 0.1)'
    return 'rgba(239, 68, 68, 0.1)'
  }

  const formatScore = (score: number | null) => {
    if (score === null) return '-'
    return (score * 100).toFixed(0) + '%'
  }

  const getQueryForEval = (evaluation: Evaluation) => {
    if (!evaluation.retrieval_id) return null
    return retrievalQueryMap[evaluation.retrieval_id]
  }

  return (
    <div className="h-full overflow-auto p-6" style={{ background: 'var(--background)' }}>
      {/* Stats Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="console-card p-4">
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
            Total Evaluations
          </div>
          <div className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
            {stats.total}
          </div>
        </div>
        <div className="console-card p-4">
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
            Avg Score
          </div>
          <div className="text-2xl font-semibold" style={{ color: getScoreColor(stats.avgScore) }}>
            {formatScore(stats.avgScore)}
          </div>
        </div>
        <div className="console-card p-4">
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--success)' }}>
            Passed (&ge;70%)
          </div>
          <div className="text-2xl font-semibold" style={{ color: 'var(--success)' }}>
            {stats.passCount}
          </div>
        </div>
        <div className="console-card p-4">
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--error)' }}>
            Failed (&lt;50%)
          </div>
          <div className="text-2xl font-semibold" style={{ color: 'var(--error)' }}>
            {stats.failCount}
          </div>
        </div>
        <div className="console-card p-4">
          <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
            Agents
          </div>
          <div className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
            {stats.agentCount}
          </div>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Main List */}
        <div className={`console-card flex-1 ${selectedEval ? 'max-w-[60%]' : ''}`}>
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                Evaluations
              </span>
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{ background: 'var(--background-subtle)', color: 'var(--text-muted)' }}
              >
                {filteredEvaluations?.length || 0}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {/* Type Filter */}
              <div className="flex items-center gap-1">
                <Button
                  variant={typeFilter === null ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    setTypeFilter(null)
                    setEvaluationsPage(1)
                  }}
                  className="h-7 text-xs"
                >
                  All
                </Button>
                {evalTypes.map((type) => {
                  const Icon = EVAL_TYPE_ICONS[type] || Star
                  return (
                    <Button
                      key={type}
                      variant={typeFilter === type ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setTypeFilter(type)
                        setEvaluationsPage(1)
                      }}
                      className="h-7 text-xs gap-1"
                    >
                      <Icon className="w-3 h-3" />
                      {EVAL_TYPE_LABELS[type] || type}
                    </Button>
                  )
                })}
              </div>
              {/* Search */}
              <div className="relative">
                <Search
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5"
                  style={{ color: 'var(--text-muted)' }}
                />
                <Input
                  placeholder="Search queries, reasoning..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setEvaluationsPage(1)
                  }}
                  className="pl-8 h-7 w-56 text-xs"
                  style={{ background: 'var(--background)', borderColor: 'var(--border)' }}
                />
              </div>
            </div>
          </div>

          {/* List */}
          {paginatedEvaluations && paginatedEvaluations.length > 0 ? (
            <>
              <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {paginatedEvaluations.map((evaluation) => {
                  const Icon = EVAL_TYPE_ICONS[evaluation.evaluation_type] || Star
                  const queryInfo = getQueryForEval(evaluation)
                  const isExpanded = expandedId === evaluation.id
                  const isSelected = selectedEval?.id === evaluation.id

                  return (
                    <div
                      key={evaluation.id}
                      className="transition-colors cursor-pointer"
                      style={{
                        background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                        borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                      }}
                      onClick={() => setSelectedEval(isSelected ? null : evaluation)}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.currentTarget.style.background = 'var(--surface-hover)'
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      <div className="px-4 py-3">
                        {/* Main row */}
                        <div className="flex items-start gap-3">
                          {/* Score badge */}
                          <div
                            className="w-12 h-12 rounded-lg flex flex-col items-center justify-center shrink-0"
                            style={{ background: getScoreBg(evaluation.score) }}
                          >
                            <span
                              className="text-lg font-bold mono"
                              style={{ color: getScoreColor(evaluation.score) }}
                            >
                              {evaluation.score !== null ? Math.round(evaluation.score * 100) : '-'}
                            </span>
                            {evaluation.score !== null && (
                              <span className="text-[9px] uppercase" style={{ color: getScoreColor(evaluation.score) }}>
                                {evaluation.score >= 0.7 ? 'pass' : evaluation.score >= 0.5 ? 'warn' : 'fail'}
                              </span>
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            {/* Query text */}
                            {queryInfo?.query ? (
                              <div className="flex items-start gap-2 mb-1">
                                <MessageSquare className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: 'var(--accent)' }} />
                                <span className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                                  {queryInfo.query}
                                </span>
                              </div>
                            ) : (
                              <div className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                                {evaluation.metric_name || evaluation.category || 'Experiment-level evaluation'}
                              </div>
                            )}

                            {/* Metric & Type */}
                            <div className="flex items-center gap-2 mb-1">
                              <span
                                className="text-xs px-1.5 py-0.5 rounded flex items-center gap-1"
                                style={{ background: 'var(--background-subtle)', color: 'var(--text-secondary)' }}
                              >
                                <Icon className="w-3 h-3" />
                                {evaluation.metric_name || EVAL_TYPE_LABELS[evaluation.evaluation_type]}
                              </span>
                              {evaluation.agent_name && (
                                <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                                  <Bot className="w-3 h-3" />
                                  {evaluation.agent_name}
                                </span>
                              )}
                              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                {formatTime(evaluation.created_at)}
                              </span>
                            </div>

                            {/* Reasoning preview */}
                            {evaluation.reasoning && (
                              <p
                                className="text-xs line-clamp-2"
                                style={{ color: 'var(--text-muted)' }}
                              >
                                {evaluation.reasoning}
                              </p>
                            )}
                          </div>

                          {/* Expand button */}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              setExpandedId(isExpanded ? null : evaluation.id)
                            }}
                          >
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                            ) : (
                              <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                            )}
                          </Button>
                        </div>

                        {/* Expanded content */}
                        {isExpanded && (
                          <div
                            className="mt-3 pt-3 pl-15"
                            style={{ borderTop: '1px solid var(--border)', marginLeft: '60px' }}
                          >
                            {evaluation.reasoning && (
                              <div className="mb-3">
                                <div className="text-xs font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
                                  Reasoning
                                </div>
                                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                  {evaluation.reasoning}
                                </p>
                              </div>
                            )}
                            {queryInfo?.response && (
                              <div>
                                <div className="text-xs font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
                                  LLM Response
                                </div>
                                <p className="text-xs mono p-2 rounded" style={{ background: 'var(--background)', color: 'var(--text-secondary)' }}>
                                  {queryInfo.response.slice(0, 500)}{queryInfo.response.length > 500 ? '...' : ''}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div
                  className="flex items-center justify-between px-4 py-3"
                  style={{ borderTop: '1px solid var(--border)' }}
                >
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {(evaluationsPage - 1) * PAGE_SIZE + 1}–{Math.min(evaluationsPage * PAGE_SIZE, filteredEvaluations?.length || 0)} of {filteredEvaluations?.length || 0}
                  </span>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setEvaluationsPage(evaluationsPage - 1)}
                      disabled={evaluationsPage === 1}
                      className="h-7 w-7"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </Button>
                    <span className="text-xs px-2" style={{ color: 'var(--text-secondary)' }}>
                      {evaluationsPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setEvaluationsPage(evaluationsPage + 1)}
                      disabled={evaluationsPage === totalPages}
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
                <BarChart3 className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
              </div>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {searchTerm || typeFilter ? 'No evaluations match your filters' : 'No evaluations yet'}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                Use an AI agent to run evaluations on your queries
              </p>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selectedEval && (
          <div className="console-card w-[40%] max-h-[calc(100vh-200px)] overflow-auto">
            <div
              className="flex items-center justify-between px-4 py-3 sticky top-0"
              style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}
            >
              <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                Evaluation Details
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setSelectedEval(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="p-4 space-y-4">
              {/* Score */}
              <div className="flex items-center gap-4">
                <div
                  className="w-20 h-20 rounded-xl flex flex-col items-center justify-center"
                  style={{ background: getScoreBg(selectedEval.score) }}
                >
                  <span
                    className="text-3xl font-bold mono"
                    style={{ color: getScoreColor(selectedEval.score) }}
                  >
                    {selectedEval.score !== null ? Math.round(selectedEval.score * 100) : '-'}
                  </span>
                  <span className="text-xs" style={{ color: getScoreColor(selectedEval.score) }}>
                    {selectedEval.score !== null
                      ? selectedEval.score >= 0.7 ? 'PASSED' : selectedEval.score >= 0.5 ? 'WARNING' : 'FAILED'
                      : 'N/A'}
                  </span>
                </div>
                <div>
                  <div className="text-lg font-medium" style={{ color: 'var(--text-primary)' }}>
                    {selectedEval.metric_name || EVAL_TYPE_LABELS[selectedEval.evaluation_type]}
                  </div>
                  <div className="text-xs flex items-center gap-2 mt-1" style={{ color: 'var(--text-muted)' }}>
                    {selectedEval.agent_name && (
                      <span className="flex items-center gap-1">
                        <Bot className="w-3 h-3" />
                        {selectedEval.agent_name}
                      </span>
                    )}
                    <span>{formatTime(selectedEval.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Query */}
              {getQueryForEval(selectedEval)?.query && (
                <div>
                  <div className="text-xs font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
                    Query
                  </div>
                  <div
                    className="p-3 rounded-lg text-sm"
                    style={{ background: 'var(--background)', color: 'var(--text-primary)' }}
                  >
                    {getQueryForEval(selectedEval)?.query}
                  </div>
                </div>
              )}

              {/* Reasoning */}
              {selectedEval.reasoning && (
                <div>
                  <div className="text-xs font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
                    Reasoning
                  </div>
                  <div
                    className="p-3 rounded-lg text-sm"
                    style={{ background: 'var(--background)', color: 'var(--text-secondary)' }}
                  >
                    {selectedEval.reasoning}
                  </div>
                </div>
              )}

              {/* LLM Response */}
              {getQueryForEval(selectedEval)?.response && (
                <div>
                  <div className="text-xs font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
                    LLM Response (Evaluated)
                  </div>
                  <div
                    className="p-3 rounded-lg text-xs mono max-h-48 overflow-auto"
                    style={{ background: 'var(--background)', color: 'var(--text-secondary)' }}
                  >
                    {getQueryForEval(selectedEval)?.response}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {selectedEval.metadata && Object.keys(selectedEval.metadata).length > 0 && (
                <div>
                  <div className="text-xs font-medium uppercase mb-2" style={{ color: 'var(--text-muted)' }}>
                    Metadata
                  </div>
                  <pre
                    className="p-3 rounded-lg text-xs mono overflow-auto"
                    style={{ background: 'var(--background)', color: 'var(--text-secondary)' }}
                  >
                    {JSON.stringify(selectedEval.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
