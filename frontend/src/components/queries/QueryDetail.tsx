import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Search,
  Layers,
  Cpu,
  FileText,
  ChevronDown,
  ChevronUp,
  Eye,
  Copy,
  Check,
  Clock,
  MessageSquare,
  User,
  Bot,
  AlertCircle,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SourceSidebar } from './SourceSidebar'
import { useAppStore } from '@/store'
import { formatLatency, formatTime, getLatencyColor } from '@/lib/utils'
import type { DashboardData, LLMCall, RetrievalResult } from '@/api/types'

interface QueryDetailProps {
  data: DashboardData
}

// Get color based on chunk rank (top chunks get accent colors)
function getChunkColor(idx: number): { bg: string; border: string; text: string } {
  if (idx === 0) return { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.3)', text: 'rgb(59, 130, 246)' }
  if (idx === 1) return { bg: 'rgba(99, 102, 241, 0.08)', border: 'rgba(99, 102, 241, 0.25)', text: 'rgb(99, 102, 241)' }
  if (idx === 2) return { bg: 'rgba(139, 92, 246, 0.06)', border: 'rgba(139, 92, 246, 0.2)', text: 'rgb(139, 92, 246)' }
  if (idx < 5) return { bg: 'rgba(168, 85, 247, 0.04)', border: 'rgba(168, 85, 247, 0.15)', text: 'rgb(168, 85, 247)' }
  return { bg: 'var(--background-subtle)', border: 'var(--border)', text: 'var(--text-secondary)' }
}

// Format score with color indication
function getScoreColor(score: number): string {
  if (score >= 0.8) return 'rgb(34, 197, 94)' // green
  if (score >= 0.6) return 'rgb(234, 179, 8)' // yellow
  if (score >= 0.4) return 'rgb(249, 115, 22)' // orange
  return 'var(--text-muted)'
}

// Collapsed chunk component - shows minimal info, click to expand
function CollapsedChunk({
  chunk,
  idx,
  onExpand,
  data,
}: {
  chunk: RetrievalResult
  idx: number
  onExpand: () => void
  data: DashboardData
}) {
  const colors = getChunkColor(idx)
  const score = chunk.score ?? 0

  return (
    <button
      onClick={onExpand}
      className="w-full p-3 rounded-lg border text-left hover:brightness-95 transition-all"
      style={{ borderColor: colors.border, background: colors.bg }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-6 h-6 rounded flex items-center justify-center text-xs font-semibold"
          style={{ background: colors.border, color: idx < 5 ? colors.text : 'var(--text-secondary)' }}
        >
          {idx + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium" style={{ color: getScoreColor(score) }}>
              {score.toFixed(3)}
            </span>
            {chunk.page_number && (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Page {chunk.page_number}
              </span>
            )}
            <span className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
              {data.documents[chunk.doc_id]?.filename ?? chunk.doc_id}
            </span>
          </div>
          <p className="text-sm truncate mt-1" style={{ color: 'var(--text-secondary)' }}>
            {chunk.text}
          </p>
        </div>
        <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
      </div>
    </button>
  )
}

// Expanded chunk component - shows full details
function ExpandedChunk({
  chunk,
  idx,
  data,
  onCollapse,
  onCopy,
  copiedId,
  onViewSource,
  canCollapse,
}: {
  chunk: RetrievalResult
  idx: number
  data: DashboardData
  onCollapse?: () => void
  onCopy: (text: string, id: string) => void
  copiedId: string | null
  onViewSource: (docId: string, pageNumber?: number | null, chunkText?: string) => void
  canCollapse: boolean
}) {
  const colors = getChunkColor(idx)
  const score = chunk.score ?? 0

  return (
    <div
      className="p-4 rounded-lg border-l-4"
      style={{
        borderLeftColor: idx < 5 ? colors.text : 'var(--border)',
        borderTop: `1px solid ${colors.border}`,
        borderRight: `1px solid ${colors.border}`,
        borderBottom: `1px solid ${colors.border}`,
        background: colors.bg,
      }}
    >
      {/* Chunk Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded flex items-center justify-center text-sm font-semibold"
            style={{ background: colors.border, color: idx < 5 ? colors.text : 'var(--text-secondary)' }}
          >
            {idx + 1}
          </div>
          <span className="text-sm font-medium" style={{ color: getScoreColor(score) }}>
            {score.toFixed(3)}
          </span>
          {chunk.page_number && (
            <Badge variant="outline" className="text-xs">
              Page {chunk.page_number}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 gap-1 text-xs"
            onClick={() => onCopy(chunk.text, chunk.chunk_id)}
          >
            {copiedId === chunk.chunk_id ? (
              <Check className="w-3 h-3" style={{ color: 'var(--success)' }} />
            ) : (
              <Copy className="w-3 h-3" />
            )}
            Copy
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 gap-1 text-xs"
            onClick={() => onViewSource(chunk.doc_id, chunk.page_number, chunk.text)}
          >
            <Eye className="w-3 h-3" />
            View
          </Button>
          {canCollapse && onCollapse && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onCollapse}
            >
              <ChevronUp className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Chunk Text */}
      <div
        className="rounded p-3 mb-3 text-sm leading-relaxed border"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
      >
        {chunk.text}
      </div>

      {/* Source Doc */}
      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        <FileText className="w-3.5 h-3.5" />
        <span>{data.documents[chunk.doc_id]?.filename ?? chunk.doc_id}</span>
        {chunk.start_char_idx != null && chunk.end_char_idx != null && (
          <span>(chars {chunk.start_char_idx} - {chunk.end_char_idx})</span>
        )}
      </div>
    </div>
  )
}

export function QueryDetail({ data }: QueryDetailProps) {
  const { queryId } = useParams<{ queryId: string }>()
  const navigate = useNavigate()
  const { currentExperimentId, sidebarDocId, openSourceSidebar } = useAppStore()
  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set([0, 1, 2, 3, 4])) // First 5 expanded
  const [showAllChunks, setShowAllChunks] = useState(false)
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    prompt: true,
    response: true,
  })

  const retrieval = useMemo(() => {
    return data.retrievals.find((r) => r.id === Number(queryId))
  }, [data.retrievals, queryId])

  // Find associated LLM call by retrieval_id (direct link)
  const llmCall = useMemo(() => {
    if (!retrieval) return null

    // Primary: Match by retrieval_id (proper linking)
    if (retrieval.retrieval_id) {
      const match = data.llm_calls.find((l) => l.retrieval_id === retrieval.retrieval_id)
      if (match) return match
    }

    // Fallback: Try trace_id match
    if (retrieval.trace_id) {
      const match = data.llm_calls.find((l) => l.trace_id === retrieval.trace_id)
      if (match) return match
    }

    // Last resort: timestamp proximity (for old data without retrieval_id)
    const retrievalTime = new Date(retrieval.timestamp).getTime()
    const closestCall = data.llm_calls
      .filter((l) => {
        const llmTime = new Date(l.timestamp).getTime()
        return llmTime > retrievalTime && llmTime - retrievalTime < 10000
      })
      .sort((a, b) => {
        const aTime = new Date(a.timestamp).getTime() - retrievalTime
        const bTime = new Date(b.timestamp).getTime() - retrievalTime
        return aTime - bTime
      })[0]

    return closestCall || null
  }, [data.llm_calls, retrieval])

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  const toggleChunk = (idx: number) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  const handleBack = () => {
    const basePath = currentExperimentId ? `/experiment/${currentExperimentId}` : '/experiment/all'
    navigate(`${basePath}/queries`)
  }

  const handleViewSource = (docId: string, pageNumber?: number | null, chunkText?: string) => {
    openSourceSidebar(docId, pageNumber ?? 1, chunkText ?? undefined)
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedText(id)
    setTimeout(() => setCopiedText(null), 2000)
  }

  // Parse messages from LLM call
  const parseMessages = (llmCall: LLMCall): { role: string; content: string }[] => {
    if (llmCall.messages && Array.isArray(llmCall.messages)) {
      return llmCall.messages
    }
    if (llmCall.prompt) {
      return [{ role: 'user', content: llmCall.prompt }]
    }
    return []
  }

  if (!retrieval) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <p style={{ color: 'var(--text-secondary)' }}>Query not found</p>
            <Button variant="outline" className="mt-4" onClick={handleBack}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Queries
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show first 10 chunks by default, or all if showAllChunks is true
  const INITIAL_CHUNKS = 10
  const displayedChunks = showAllChunks
    ? retrieval.results
    : retrieval.results.slice(0, INITIAL_CHUNKS)

  const messages = llmCall ? parseMessages(llmCall) : []

  return (
    <div className="h-full flex overflow-hidden">
      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-5 max-w-5xl">
          {/* Header */}
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={handleBack} className="gap-1.5 h-8">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back
            </Button>
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="gap-1 px-2 py-0.5 text-xs">
                <Layers className="w-3 h-3" />
                {retrieval.num_results} chunks
              </Badge>
              <Badge variant="outline" className="gap-1 px-2 py-0.5 text-xs">
                <Clock className="w-3 h-3" />
                {formatLatency(retrieval.duration_ms)}
              </Badge>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {formatTime(retrieval.timestamp)}
              </span>
            </div>
          </div>

          {/* Query Section */}
          <Card>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                <Search className="w-4 h-4" />
                User Query
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-base leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                {retrieval.query}
              </p>
            </CardContent>
          </Card>

          {/* LLM Call Section */}
          {llmCall ? (
            <Card>
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <Cpu className="w-4 h-4" />
                    LLM Call Details
                  </CardTitle>
                  <Badge variant={llmCall.status === 'success' ? 'secondary' : 'destructive'} className="text-xs">
                    {llmCall.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 px-4 pb-4">
                {/* Model Info Bar */}
                <div
                  className="flex items-center gap-4 p-3 rounded-lg"
                  style={{ background: 'var(--background-subtle)' }}
                >
                  <div className="flex-1">
                    <div className="font-medium">{llmCall.model}</div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {llmCall.input_type === 'chat' ? 'Chat Completion' : 'Completion'} API
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-lg font-semibold ${getLatencyColor(llmCall.duration_ms)}`}>
                      {formatLatency(llmCall.duration_ms)}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      Latency
                    </div>
                  </div>
                </div>

                {/* Token Stats */}
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: 'Prompt Tokens', value: llmCall.prompt_tokens ?? 0 },
                    { label: 'Completion Tokens', value: llmCall.completion_tokens ?? 0 },
                    { label: 'Total Tokens', value: llmCall.total_tokens ?? 0 },
                    { label: 'Temperature', value: llmCall.temperature ?? 0 },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className="p-3 rounded-lg text-center"
                      style={{ background: 'var(--background-subtle)' }}
                    >
                      <div className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {stat.value}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {stat.label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Prompt / Messages */}
                <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'var(--border)' }}>
                  <button
                    onClick={() => toggleSection('prompt')}
                    className="w-full flex items-center justify-between p-3 hover:bg-[var(--surface-hover)] transition-colors"
                    style={{ background: 'var(--background-subtle)' }}
                  >
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <MessageSquare className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                      Input Prompt
                      {messages.length > 0 && (
                        <Badge variant="secondary" className="ml-1 text-xs">
                          {messages.length} messages
                        </Badge>
                      )}
                    </div>
                    {expandedSections.prompt ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                  {expandedSections.prompt && (
                    <div className="p-3 space-y-2 max-h-80 overflow-auto">
                      {messages.length > 0 ? (
                        messages.map((msg, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg border"
                            style={{
                              background: 'var(--surface)',
                              borderColor: 'var(--border)',
                            }}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              {msg.role === 'user' ? (
                                <User className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                              ) : msg.role === 'system' ? (
                                <AlertCircle className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                              ) : (
                                <Bot className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                              )}
                              <span
                                className="text-xs font-medium uppercase"
                                style={{ color: 'var(--text-muted)' }}
                              >
                                {msg.role}
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="ml-auto h-6 px-2"
                                onClick={() => copyToClipboard(msg.content, `msg-${idx}`)}
                              >
                                {copiedText === `msg-${idx}` ? (
                                  <Check className="w-3 h-3" style={{ color: 'var(--success)' }} />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </Button>
                            </div>
                            <pre className="text-sm whitespace-pre-wrap font-mono">{msg.content}</pre>
                          </div>
                        ))
                      ) : llmCall.prompt ? (
                        <div
                          className="p-3 rounded-lg border"
                          style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
                        >
                          <pre className="text-sm whitespace-pre-wrap font-mono">{llmCall.prompt}</pre>
                        </div>
                      ) : (
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                          No prompt data available
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Response */}
                <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'var(--border)' }}>
                  <button
                    onClick={() => toggleSection('response')}
                    className="w-full flex items-center justify-between p-3 hover:bg-[var(--surface-hover)] transition-colors"
                    style={{ background: 'var(--background-subtle)' }}
                  >
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Bot className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                      LLM Response
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          copyToClipboard(llmCall.response, 'response')
                        }}
                      >
                        {copiedText === 'response' ? (
                          <Check className="w-3 h-3" style={{ color: 'var(--success)' }} />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </Button>
                      {expandedSections.response ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </button>
                  {expandedSections.response && (
                    <div className="p-3 max-h-80 overflow-auto">
                      <div
                        className="p-3 rounded-lg"
                        style={{ background: 'var(--surface)' }}
                      >
                        <pre className="text-sm whitespace-pre-wrap font-mono">{llmCall.response}</pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* Error */}
                {llmCall.error && (
                  <div
                    className="p-3 rounded-lg border"
                    style={{ background: 'var(--error-subtle)', borderColor: 'var(--error)' }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <AlertCircle className="w-4 h-4" style={{ color: 'var(--error)' }} />
                      <span className="font-medium text-sm" style={{ color: 'var(--error)' }}>
                        Error
                      </span>
                    </div>
                    <p className="text-sm" style={{ color: 'var(--error)' }}>
                      {llmCall.error}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <Cpu className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text-muted)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No LLM call found for this query</p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  The retrieval may not have triggered an LLM call
                </p>
              </CardContent>
            </Card>
          )}

          {/* Source Attribution - Retrieved Chunks */}
          <Card>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                <Layers className="w-4 h-4" />
                Source Attribution ({retrieval.results.length} chunks retrieved)
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="space-y-2">
                {displayedChunks.map((chunk, idx) =>
                  expandedChunks.has(idx) ? (
                    <ExpandedChunk
                      key={`${chunk.chunk_id}-${idx}`}
                      chunk={chunk}
                      idx={idx}
                      data={data}
                      onCollapse={idx >= 5 ? () => toggleChunk(idx) : undefined}
                      onCopy={copyToClipboard}
                      copiedId={copiedText}
                      onViewSource={handleViewSource}
                      canCollapse={idx >= 5}
                    />
                  ) : (
                    <CollapsedChunk
                      key={`${chunk.chunk_id}-${idx}`}
                      chunk={chunk}
                      idx={idx}
                      onExpand={() => toggleChunk(idx)}
                      data={data}
                    />
                  )
                )}

                {retrieval.results.length > INITIAL_CHUNKS && (
                  <Button
                    variant="outline"
                    className="w-full h-10 text-sm"
                    onClick={() => setShowAllChunks(!showAllChunks)}
                  >
                    {showAllChunks ? (
                      <>
                        <ChevronUp className="w-4 h-4 mr-2" />
                        Show Less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-4 h-4 mr-2" />
                        Show All ({retrieval.results.length - INITIAL_CHUNKS} more)
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>

      {/* Source Sidebar */}
      {sidebarDocId && <SourceSidebar data={data} />}
    </div>
  )
}
