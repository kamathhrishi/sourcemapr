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
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SourceSidebar } from './SourceSidebar'
import { useAppStore } from '@/store'
import { formatLatency, formatTime, getLatencyColor } from '@/lib/utils'
import type { DashboardData, LLMCall } from '@/api/types'

interface QueryDetailProps {
  data: DashboardData
}

export function QueryDetail({ data }: QueryDetailProps) {
  const { queryId } = useParams<{ queryId: string }>()
  const navigate = useNavigate()
  const { currentExperimentId, sidebarDocId, openSourceSidebar } = useAppStore()
  const [showAllChunks, setShowAllChunks] = useState(false)
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    prompt: true,
    response: true,
  })

  const retrieval = useMemo(() => {
    return data.retrievals.find((r) => r.id === Number(queryId))
  }, [data.retrievals, queryId])

  // Find associated LLM call - try trace_id first, then timestamp proximity
  const llmCall = useMemo(() => {
    if (!retrieval) return null

    // Try trace_id match first
    if (retrieval.trace_id) {
      const match = data.llm_calls.find((l) => l.trace_id === retrieval.trace_id)
      if (match) return match
    }

    // Fall back to timestamp proximity (within 5 seconds)
    const retrievalTime = new Date(retrieval.timestamp).getTime()
    const closestCall = data.llm_calls
      .filter(l => {
        const llmTime = new Date(l.timestamp).getTime()
        return Math.abs(llmTime - retrievalTime) < 5000 // within 5 seconds
      })
      .sort((a, b) => {
        const aTime = Math.abs(new Date(a.timestamp).getTime() - retrievalTime)
        const bTime = Math.abs(new Date(b.timestamp).getTime() - retrievalTime)
        return aTime - bTime
      })[0]

    return closestCall || null
  }, [data.llm_calls, retrieval])

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const handleBack = () => {
    const basePath = currentExperimentId
      ? `/experiment/${currentExperimentId}`
      : '/experiment/all'
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
            <p className="text-apple-secondary">Query not found</p>
            <Button variant="outline" className="mt-4" onClick={handleBack}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Queries
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const displayedChunks = showAllChunks
    ? retrieval.results
    : retrieval.results.slice(0, 5)

  const messages = llmCall ? parseMessages(llmCall) : []

  return (
    <div className="h-full flex overflow-hidden">
      {/* Main Content */}
      <ScrollArea className={`flex-1 ${sidebarDocId ? '' : ''}`}>
        <div className="p-6 space-y-6 max-w-6xl">
          {/* Header */}
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm" onClick={handleBack} className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <div className="flex-1" />
            <div className="flex items-center gap-3">
              <Badge variant="secondary" className="gap-1.5 px-3 py-1">
                <Layers className="w-3.5 h-3.5" />
                {retrieval.num_results} chunks
              </Badge>
              <Badge
                variant={retrieval.duration_ms < 500 ? 'success' : retrieval.duration_ms < 2000 ? 'warning' : 'destructive'}
                className="gap-1.5 px-3 py-1"
              >
                <Clock className="w-3.5 h-3.5" />
                {formatLatency(retrieval.duration_ms)}
              </Badge>
              <span className="text-sm text-apple-secondary">{formatTime(retrieval.timestamp)}</span>
            </div>
          </div>

          {/* Query Section */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="w-4 h-4 text-purple-500" />
                User Query
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-950/30 dark:to-indigo-950/30 p-4 rounded-lg border border-purple-100 dark:border-purple-900">
                <p className="text-base leading-relaxed">{retrieval.query}</p>
              </div>
            </CardContent>
          </Card>

          {/* LLM Call Section */}
          {llmCall ? (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-orange-500" />
                    LLM Call Details
                  </CardTitle>
                  <Badge variant={llmCall.status === 'success' ? 'success' : 'destructive'}>
                    {llmCall.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Model Info Bar */}
                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 rounded-lg border border-orange-100 dark:border-orange-900">
                  <div className="w-12 h-12 rounded-xl bg-orange-100 dark:bg-orange-900/50 flex items-center justify-center">
                    <Cpu className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-lg">{llmCall.model}</div>
                    <div className="text-sm text-apple-secondary">
                      {llmCall.input_type === 'chat' ? 'Chat Completion' : 'Completion'} API
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xl font-bold ${getLatencyColor(llmCall.duration_ms)}`}>
                      {formatLatency(llmCall.duration_ms)}
                    </div>
                    <div className="text-xs text-apple-secondary">Latency</div>
                  </div>
                </div>

                {/* Token Stats */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-4 bg-apple-tertiary rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{llmCall.prompt_tokens ?? 0}</div>
                    <div className="text-xs text-apple-secondary mt-1">Prompt Tokens</div>
                  </div>
                  <div className="p-4 bg-apple-tertiary rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">{llmCall.completion_tokens ?? 0}</div>
                    <div className="text-xs text-apple-secondary mt-1">Completion Tokens</div>
                  </div>
                  <div className="p-4 bg-apple-tertiary rounded-lg text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{llmCall.total_tokens ?? 0}</div>
                    <div className="text-xs text-apple-secondary mt-1">Total Tokens</div>
                  </div>
                  <div className="p-4 bg-apple-tertiary rounded-lg text-center">
                    <div className="text-2xl font-bold">{llmCall.temperature ?? 0}</div>
                    <div className="text-xs text-apple-secondary mt-1">Temperature</div>
                  </div>
                </div>

                {/* Prompt / Messages */}
                <div className="border border-apple-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleSection('prompt')}
                    className="w-full flex items-center justify-between p-4 bg-apple-tertiary/50 hover:bg-apple-tertiary transition-colors"
                  >
                    <div className="flex items-center gap-2 font-medium">
                      <MessageSquare className="w-4 h-4 text-blue-500" />
                      Input Prompt
                      {messages.length > 0 && (
                        <Badge variant="secondary" className="ml-2">{messages.length} messages</Badge>
                      )}
                    </div>
                    {expandedSections.prompt ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.prompt && (
                    <div className="p-4 space-y-3 max-h-96 overflow-auto">
                      {messages.length > 0 ? (
                        messages.map((msg, idx) => (
                          <div key={idx} className={`p-3 rounded-lg ${
                            msg.role === 'user'
                              ? 'bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900'
                              : msg.role === 'system'
                              ? 'bg-gray-50 dark:bg-gray-900/30 border border-gray-200 dark:border-gray-800'
                              : 'bg-green-50 dark:bg-green-950/30 border border-green-100 dark:border-green-900'
                          }`}>
                            <div className="flex items-center gap-2 mb-2">
                              {msg.role === 'user' ? (
                                <User className="w-4 h-4 text-blue-500" />
                              ) : msg.role === 'system' ? (
                                <AlertCircle className="w-4 h-4 text-gray-500" />
                              ) : (
                                <Bot className="w-4 h-4 text-green-500" />
                              )}
                              <span className="text-xs font-medium uppercase text-apple-secondary">{msg.role}</span>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="ml-auto h-6 px-2"
                                onClick={() => copyToClipboard(msg.content, `msg-${idx}`)}
                              >
                                {copiedText === `msg-${idx}` ? (
                                  <Check className="w-3 h-3 text-green-500" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </Button>
                            </div>
                            <pre className="text-sm whitespace-pre-wrap font-mono">{msg.content}</pre>
                          </div>
                        ))
                      ) : llmCall.prompt ? (
                        <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900">
                          <pre className="text-sm whitespace-pre-wrap font-mono">{llmCall.prompt}</pre>
                        </div>
                      ) : (
                        <p className="text-apple-secondary text-sm">No prompt data available</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Response */}
                <div className="border border-apple-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleSection('response')}
                    className="w-full flex items-center justify-between p-4 bg-apple-tertiary/50 hover:bg-apple-tertiary transition-colors"
                  >
                    <div className="flex items-center gap-2 font-medium">
                      <Bot className="w-4 h-4 text-green-500" />
                      LLM Response
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          copyToClipboard(llmCall.response, 'response')
                        }}
                      >
                        {copiedText === 'response' ? (
                          <Check className="w-3 h-3 text-green-500" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </Button>
                      {expandedSections.response ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </button>
                  {expandedSections.response && (
                    <div className="p-4 max-h-96 overflow-auto">
                      <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-100 dark:border-green-900">
                        <pre className="text-sm whitespace-pre-wrap font-mono">{llmCall.response}</pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* Error */}
                {llmCall.error && (
                  <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-red-500" />
                      <span className="font-medium text-red-600 dark:text-red-400">Error</span>
                    </div>
                    <p className="text-sm text-red-600 dark:text-red-400">{llmCall.error}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <Cpu className="w-10 h-10 mx-auto mb-3 text-apple-secondary" />
                <p className="text-apple-secondary">No LLM call found for this query</p>
                <p className="text-xs text-apple-secondary mt-1">The retrieval may not have triggered an LLM call</p>
              </CardContent>
            </Card>
          )}

          {/* Source Attribution - Retrieved Chunks */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-500" />
                Source Attribution ({retrieval.results.length} chunks retrieved)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {displayedChunks.map((chunk, idx) => (
                  <div
                    key={`${chunk.chunk_id}-${idx}`}
                    className="p-4 rounded-xl border border-apple-border hover:border-blue-300 dark:hover:border-blue-700 transition-colors bg-apple-card"
                  >
                    {/* Chunk Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                          <span className="text-sm font-bold text-blue-600 dark:text-blue-400">#{idx + 1}</span>
                        </div>
                        <Badge variant="secondary" className="gap-1">
                          Score: {chunk.score.toFixed(3)}
                        </Badge>
                        {chunk.page_number && (
                          <Badge variant="outline">Page {chunk.page_number}</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 gap-1.5"
                          onClick={() => copyToClipboard(chunk.text, chunk.chunk_id)}
                        >
                          {copiedText === chunk.chunk_id ? (
                            <Check className="w-3.5 h-3.5 text-green-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                          Copy
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 gap-1.5"
                          onClick={() => handleViewSource(chunk.doc_id, chunk.page_number, chunk.text)}
                        >
                          <Eye className="w-3.5 h-3.5" />
                          View Source
                        </Button>
                      </div>
                    </div>

                    {/* Chunk Text */}
                    <div className="bg-apple-tertiary/50 rounded-lg p-3 mb-3">
                      <p className="text-sm leading-relaxed">{chunk.text}</p>
                    </div>

                    {/* Source Doc */}
                    <div className="flex items-center gap-2 text-sm text-apple-secondary">
                      <FileText className="w-4 h-4" />
                      <span className="font-medium">{data.documents[chunk.doc_id]?.filename ?? chunk.doc_id}</span>
                      {chunk.start_char_idx != null && chunk.end_char_idx != null && (
                        <span className="text-xs">
                          (chars {chunk.start_char_idx} - {chunk.end_char_idx})
                        </span>
                      )}
                    </div>
                  </div>
                ))}

                {retrieval.results.length > 5 && (
                  <Button
                    variant="outline"
                    className="w-full h-12"
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
                        Show All Chunks ({retrieval.results.length - 5} more)
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
