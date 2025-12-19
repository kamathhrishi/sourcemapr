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

  const retrieval = useMemo(() => {
    return data.retrievals.find((r) => r.id === Number(queryId))
  }, [data.retrievals, queryId])

  const llmCall = useMemo(() => {
    if (!retrieval?.trace_id) return null
    return data.llm_calls.find((l) => l.trace_id === retrieval.trace_id)
  }, [data.llm_calls, retrieval?.trace_id])

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

  return (
    <div className="h-full flex overflow-hidden">
      {/* Main Content */}
      <div className={`flex-1 overflow-auto p-6 space-y-6 ${sidebarDocId ? '' : ''}`}>
        {/* Header */}
        <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={handleBack}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold flex items-center gap-2">
            <Search className="w-4 h-4" />
            Query Details
          </h2>
          <p className="text-sm text-apple-secondary">{formatTime(retrieval.timestamp)}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="gap-1">
            <Layers className="w-3 h-3" />
            {retrieval.num_results} chunks
          </Badge>
          <Badge variant={retrieval.duration_ms < 500 ? 'success' : retrieval.duration_ms < 2000 ? 'warning' : 'destructive'}>
            {formatLatency(retrieval.duration_ms)}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Query & Chunks */}
        <div className="lg:col-span-2 space-y-6">
          {/* Query Card */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="w-4 h-4" />
                Query
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm bg-apple-tertiary p-3 rounded-lg">{retrieval.query}</p>
            </CardContent>
          </Card>

          {/* Retrieved Chunks */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Retrieved Chunks ({retrieval.results.length})
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {displayedChunks.map((chunk, idx) => (
                  <div
                    key={`${chunk.chunk_id}-${idx}`}
                    className="p-3 rounded-lg border border-apple-border"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          #{idx + 1}
                        </Badge>
                        <Badge variant="secondary" className="text-xs">
                          Score: {chunk.score.toFixed(3)}
                        </Badge>
                        {chunk.page_number && (
                          <Badge variant="secondary" className="text-xs">
                            Page {chunk.page_number}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2"
                          onClick={() => copyToClipboard(chunk.text, chunk.chunk_id)}
                        >
                          {copiedText === chunk.chunk_id ? (
                            <Check className="w-3 h-3 text-apple-green" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2"
                          onClick={() => handleViewSource(chunk.doc_id, chunk.page_number, chunk.text)}
                          title="View source"
                        >
                          <Eye className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-sm line-clamp-4">{chunk.text}</p>
                    <div className="mt-2 text-xs text-apple-secondary flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      {data.documents[chunk.doc_id]?.filename ?? chunk.doc_id}
                    </div>
                  </div>
                ))}

                {retrieval.results.length > 5 && (
                  <Button
                    variant="outline"
                    className="w-full"
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
                        Show All ({retrieval.results.length - 5} more)
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - LLM Call */}
        <div className="space-y-6">
          {llmCall ? (
            <LLMCallCard llmCall={llmCall} copyToClipboard={copyToClipboard} copiedText={copiedText} />
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <Cpu className="w-8 h-8 mx-auto mb-2 text-apple-secondary" />
                <p className="text-sm text-apple-secondary">No LLM call for this query</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
      </div>

      {/* Source Sidebar */}
      {sidebarDocId && <SourceSidebar data={data} />}
    </div>
  )
}

function LLMCallCard({
  llmCall,
  copyToClipboard,
  copiedText,
}: {
  llmCall: LLMCall
  copyToClipboard: (text: string, id: string) => void
  copiedText: string | null
}) {
  const [showResponse, setShowResponse] = useState(false)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          LLM Call
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Model & Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium">{llmCall.model}</span>
          </div>
          <Badge variant={llmCall.status === 'success' ? 'success' : 'destructive'}>
            {llmCall.status}
          </Badge>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 bg-apple-tertiary rounded-lg text-center">
            <div className="text-lg font-semibold">{llmCall.total_tokens}</div>
            <div className="text-xs text-apple-secondary">Total Tokens</div>
          </div>
          <div className="p-2 bg-apple-tertiary rounded-lg text-center">
            <div className={`text-lg font-semibold ${getLatencyColor(llmCall.duration_ms)}`}>
              {formatLatency(llmCall.duration_ms)}
            </div>
            <div className="text-xs text-apple-secondary">Latency</div>
          </div>
          <div className="p-2 bg-apple-tertiary rounded-lg text-center">
            <div className="text-lg font-semibold">{llmCall.prompt_tokens}</div>
            <div className="text-xs text-apple-secondary">Prompt</div>
          </div>
          <div className="p-2 bg-apple-tertiary rounded-lg text-center">
            <div className="text-lg font-semibold">{llmCall.completion_tokens}</div>
            <div className="text-xs text-apple-secondary">Completion</div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="space-y-1 text-sm">
          {llmCall.temperature !== null && (
            <div className="flex justify-between">
              <span className="text-apple-secondary">Temperature</span>
              <span>{llmCall.temperature}</span>
            </div>
          )}
          {llmCall.max_tokens !== null && (
            <div className="flex justify-between">
              <span className="text-apple-secondary">Max Tokens</span>
              <span>{llmCall.max_tokens}</span>
            </div>
          )}
          {llmCall.finish_reason && (
            <div className="flex justify-between">
              <span className="text-apple-secondary">Finish Reason</span>
              <span>{llmCall.finish_reason}</span>
            </div>
          )}
        </div>

        {/* Response */}
        {llmCall.response && (
          <div>
            <Button
              variant="outline"
              size="sm"
              className="w-full mb-2"
              onClick={() => setShowResponse(!showResponse)}
            >
              {showResponse ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-2" />
                  Hide Response
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-2" />
                  Show Response
                </>
              )}
            </Button>
            {showResponse && (
              <div className="relative">
                <ScrollArea className="h-48 bg-apple-tertiary rounded-lg p-3">
                  <pre className="text-xs whitespace-pre-wrap">{llmCall.response}</pre>
                </ScrollArea>
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute top-2 right-2 h-6 px-2"
                  onClick={() => copyToClipboard(llmCall.response, 'response')}
                >
                  {copiedText === 'response' ? (
                    <Check className="w-3 h-3 text-apple-green" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {llmCall.error && (
          <div className="p-3 bg-apple-red/10 border border-apple-red/30 rounded-lg">
            <p className="text-sm text-apple-red">{llmCall.error}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
