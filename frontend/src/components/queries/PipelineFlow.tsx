import { useState, useEffect } from 'react'
import {
  Search,
  Filter,
  Layers,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Loader2,
  GitBranch,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/api/client'
import type { Pipeline, PipelineStage, StageChunk, DashboardData } from '@/api/types'
import { formatLatency } from '@/lib/utils'

interface PipelineFlowProps {
  retrievalId: string | null
  data: DashboardData
  onViewSource?: (docId: string, pageNumber?: number | null, chunkText?: string) => void
}

// Get icon for stage type
function getStageIcon(stageType: string) {
  switch (stageType) {
    case 'query_expansion':
      return <GitBranch className="w-4 h-4" />
    case 'retrieval':
      return <Search className="w-4 h-4" />
    case 'reranking':
    case 'compression':
      return <Filter className="w-4 h-4" />
    case 'filtering':
      return <Filter className="w-4 h-4" />
    case 'merge':
      return <Layers className="w-4 h-4" />
    default:
      return <Layers className="w-4 h-4" />
  }
}

// Get color for stage type
function getStageColor(stageType: string): { bg: string; border: string; text: string } {
  switch (stageType) {
    case 'query_expansion':
      return { bg: 'rgba(168, 85, 247, 0.1)', border: 'rgba(168, 85, 247, 0.3)', text: 'rgb(168, 85, 247)' }
    case 'retrieval':
      return { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.3)', text: 'rgb(59, 130, 246)' }
    case 'reranking':
    case 'compression':
      return { bg: 'rgba(34, 197, 94, 0.1)', border: 'rgba(34, 197, 94, 0.3)', text: 'rgb(34, 197, 94)' }
    case 'filtering':
      return { bg: 'rgba(249, 115, 22, 0.1)', border: 'rgba(249, 115, 22, 0.3)', text: 'rgb(249, 115, 22)' }
    case 'merge':
      return { bg: 'rgba(99, 102, 241, 0.1)', border: 'rgba(99, 102, 241, 0.3)', text: 'rgb(99, 102, 241)' }
    default:
      return { bg: 'var(--background-subtle)', border: 'var(--border)', text: 'var(--text-secondary)' }
  }
}

// Get status color for chunk
function getStatusColor(status: string): string {
  switch (status) {
    case 'kept':
      return 'rgb(34, 197, 94)' // green
    case 'filtered':
      return 'rgb(239, 68, 68)' // red
    case 'new':
      return 'rgb(59, 130, 246)' // blue
    default:
      return 'var(--text-muted)'
  }
}

// Stage chunk item
function ChunkItem({
  chunk,
  data,
  onViewSource,
}: {
  chunk: StageChunk
  data: DashboardData
  onViewSource?: (docId: string, pageNumber?: number | null, chunkText?: string) => void
}) {
  const statusColor = getStatusColor(chunk.status)
  const doc = data.documents[chunk.doc_id]

  return (
    <div
      className="p-2.5 rounded border text-xs"
      style={{
        borderColor: chunk.status === 'filtered' ? 'rgba(239, 68, 68, 0.2)' : 'var(--border)',
        background: chunk.status === 'filtered' ? 'rgba(239, 68, 68, 0.05)' : 'var(--surface)',
        opacity: chunk.status === 'filtered' ? 0.7 : 1,
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <Badge
          variant="outline"
          className="text-[10px] px-1.5 py-0"
          style={{ borderColor: statusColor, color: statusColor }}
        >
          {chunk.status}
        </Badge>
        {chunk.input_rank != null && (
          <span style={{ color: 'var(--text-muted)' }}>
            Rank: {chunk.input_rank + 1}
            {chunk.output_rank != null && chunk.output_rank !== chunk.input_rank && (
              <> → {chunk.output_rank + 1}</>
            )}
          </span>
        )}
        {chunk.input_score != null && (
          <span style={{ color: 'var(--text-muted)' }}>
            Score: {chunk.input_score.toFixed(3)}
            {chunk.output_score != null && (
              <> → {chunk.output_score.toFixed(3)}</>
            )}
          </span>
        )}
      </div>
      <p
        className="line-clamp-2 leading-relaxed mb-1.5"
        style={{ color: chunk.status === 'filtered' ? 'var(--text-muted)' : 'var(--text-secondary)' }}
      >
        {chunk.text}
      </p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
          <FileText className="w-3 h-3" />
          <span className="truncate max-w-[150px]">{doc?.filename ?? chunk.doc_id}</span>
          {chunk.source && <span>({chunk.source})</span>}
        </div>
        {onViewSource && (
          <Button
            variant="ghost"
            size="sm"
            className="h-5 px-1.5 text-[10px]"
            onClick={() => onViewSource(chunk.doc_id, null, chunk.text)}
          >
            View
          </Button>
        )}
      </div>
    </div>
  )
}

// Individual stage component
function StageCard({
  stage,
  data,
  isLast,
  onViewSource,
}: {
  stage: PipelineStage
  data: DashboardData
  isLast: boolean
  onViewSource?: (docId: string, pageNumber?: number | null, chunkText?: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const colors = getStageColor(stage.stage_type)
  const chunks = stage.chunks || []
  const keptChunks = chunks.filter((c) => c.status === 'kept' || c.status === 'new')
  const filteredChunks = chunks.filter((c) => c.status === 'filtered')

  return (
    <div className="flex items-start gap-3">
      {/* Stage Card */}
      <div
        className="flex-1 rounded-lg border overflow-hidden"
        style={{ borderColor: colors.border, background: colors.bg }}
      >
        {/* Stage Header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full p-3 flex items-center justify-between hover:brightness-95 transition-colors"
        >
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded flex items-center justify-center"
              style={{ background: colors.border, color: colors.text }}
            >
              {getStageIcon(stage.stage_type)}
            </div>
            <div className="text-left">
              <div className="font-medium text-sm">{stage.stage_name}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {stage.stage_type.replace('_', ' ')}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium">
                {stage.input_count} → {stage.output_count}
              </div>
              <div className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                <Clock className="w-3 h-3" />
                {formatLatency(stage.duration_ms)}
              </div>
            </div>
            {expanded ? (
              <ChevronUp className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            ) : (
              <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            )}
          </div>
        </button>

        {/* Expanded Chunks */}
        {expanded && chunks.length > 0 && (
          <div className="border-t px-3 pb-3 space-y-3" style={{ borderColor: colors.border }}>
            {/* Kept/New Chunks */}
            {keptChunks.length > 0 && (
              <div className="mt-3">
                <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                  Output Chunks ({keptChunks.length})
                </div>
                <div className="space-y-1.5">
                  {keptChunks.slice(0, 5).map((chunk) => (
                    <ChunkItem key={chunk.id} chunk={chunk} data={data} onViewSource={onViewSource} />
                  ))}
                  {keptChunks.length > 5 && (
                    <div className="text-xs text-center py-1" style={{ color: 'var(--text-muted)' }}>
                      +{keptChunks.length - 5} more chunks
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Filtered Chunks */}
            {filteredChunks.length > 0 && (
              <div>
                <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                  Filtered Out ({filteredChunks.length})
                </div>
                <div className="space-y-1.5">
                  {filteredChunks.slice(0, 3).map((chunk) => (
                    <ChunkItem key={chunk.id} chunk={chunk} data={data} onViewSource={onViewSource} />
                  ))}
                  {filteredChunks.length > 3 && (
                    <div className="text-xs text-center py-1" style={{ color: 'var(--text-muted)' }}>
                      +{filteredChunks.length - 3} more filtered
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Arrow to next stage */}
      {!isLast && (
        <div className="flex items-center pt-6">
          <ArrowRight className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
        </div>
      )}
    </div>
  )
}

export function PipelineFlow({ retrievalId, data, onViewSource }: PipelineFlowProps) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!retrievalId) {
      setPipeline(null)
      return
    }

    const fetchPipeline = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await api.getRetrievalPipeline(retrievalId)
        setPipeline(result)
      } catch (e) {
        setError('Failed to load pipeline')
        setPipeline(null)
      } finally {
        setLoading(false)
      }
    }

    fetchPipeline()
  }, [retrievalId])

  // Don't show anything if no retrieval_id or no pipeline
  if (!retrievalId) return null

  if (loading) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center justify-center gap-2" style={{ color: 'var(--text-muted)' }}>
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading pipeline...
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {error}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!pipeline || !pipeline.stages || !Array.isArray(pipeline.stages) || pipeline.stages.length === 0) {
    return null
  }

  // Sort stages by order
  const sortedStages = [...pipeline.stages].sort((a, b) => {
    const aOrder = a.stage_order ?? 0
    const bOrder = b.stage_order ?? 0
    return aOrder - bOrder
  })

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
            <GitBranch className="w-4 h-4" />
            RAG Pipeline ({pipeline.num_stages} stages)
          </CardTitle>
          {pipeline.total_duration_ms && (
            <Badge variant="outline" className="text-xs gap-1">
              <Clock className="w-3 h-3" />
              {formatLatency(pipeline.total_duration_ms)}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {/* Pipeline Flow */}
        <div className="flex items-start gap-1 overflow-x-auto pb-2">
          {sortedStages.map((stage, idx) => (
            <StageCard
              key={stage.stage_id}
              stage={stage}
              data={data}
              isLast={idx === sortedStages.length - 1}
              onViewSource={onViewSource}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
