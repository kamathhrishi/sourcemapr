import { FileText, Layers, Database, Search, MessageSquare, Cpu, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatTime } from '@/lib/utils'
import type { DashboardData } from '@/api/types'

interface OverviewProps {
  data: DashboardData
}

export function Overview({ data }: OverviewProps) {
  const { stats, documents, retrievals, llm_calls } = data

  const statsCards = [
    { label: 'Documents', value: stats.total_documents, icon: FileText, color: 'text-apple-blue' },
    { label: 'Chunks', value: stats.total_chunks, icon: Layers, color: 'text-apple-purple' },
    { label: 'Embeddings', value: stats.total_embeddings, icon: Database, color: 'text-apple-green' },
    { label: 'Retrievals', value: stats.total_retrievals, icon: Search, color: 'text-apple-orange' },
    { label: 'Queries', value: stats.total_traces, icon: MessageSquare, color: 'text-apple-pink' },
    { label: 'LLM Calls', value: stats.total_llm_calls, icon: Cpu, color: 'text-apple-red' },
  ]

  // Get recent items
  const recentDocs = Object.values(documents).slice(-5).reverse()
  const recentQueries = retrievals.slice(-5).reverse()

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statsCards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`${color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-semibold">{value}</div>
                  <div className="text-xs text-apple-secondary">{label}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* RAG Pipeline Flow */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">RAG Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-2 overflow-x-auto py-2">
            <PipelineStep icon={FileText} label="Documents" value={stats.total_documents} color="bg-apple-blue" />
            <ArrowRight className="w-4 h-4 text-apple-secondary shrink-0" />
            <PipelineStep icon={Layers} label="Chunks" value={stats.total_chunks} color="bg-apple-purple" />
            <ArrowRight className="w-4 h-4 text-apple-secondary shrink-0" />
            <PipelineStep icon={Database} label="Embeddings" value={stats.total_embeddings} color="bg-apple-green" />
            <ArrowRight className="w-4 h-4 text-apple-secondary shrink-0" />
            <PipelineStep icon={Search} label="Retrieval" value={stats.total_retrievals} color="bg-apple-orange" />
            <ArrowRight className="w-4 h-4 text-apple-secondary shrink-0" />
            <PipelineStep icon={Cpu} label="LLM" value={stats.total_llm_calls} color="bg-apple-red" />
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {recentDocs.length > 0 ? (
              <ul className="space-y-3">
                {recentDocs.map((doc) => (
                  <li
                    key={doc.doc_id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-apple-tertiary transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <FileText className="w-4 h-4 text-apple-secondary shrink-0" />
                      <span className="text-sm truncate">{doc.filename}</span>
                    </div>
                    <span className="text-xs text-apple-secondary shrink-0">
                      {doc.num_pages ? `${doc.num_pages} pages` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-apple-secondary text-center py-4">No documents yet</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Queries */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Queries</CardTitle>
          </CardHeader>
          <CardContent>
            {recentQueries.length > 0 ? (
              <ul className="space-y-3">
                {recentQueries.map((retrieval) => (
                  <li
                    key={retrieval.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-apple-tertiary transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Search className="w-4 h-4 text-apple-secondary shrink-0" />
                      <span className="text-sm truncate">{retrieval.query}</span>
                    </div>
                    <span className="text-xs text-apple-secondary shrink-0">
                      {formatTime(retrieval.timestamp)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-apple-secondary text-center py-4">No queries yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent LLM Calls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent LLM Calls</CardTitle>
        </CardHeader>
        <CardContent>
          {llm_calls.length > 0 ? (
            <ul className="space-y-2">
              {llm_calls.slice(-5).reverse().map((call) => (
                <li
                  key={call.id}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-apple-tertiary transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Cpu className="w-4 h-4 text-apple-secondary" />
                    <span className="text-sm font-medium">{call.model}</span>
                    <span className="text-xs text-apple-secondary">
                      {call.total_tokens} tokens
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-apple-secondary">
                      {call.duration_ms}ms
                    </span>
                    <span className="text-xs text-apple-secondary">
                      {formatTime(call.timestamp)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-apple-secondary text-center py-4">No LLM calls yet</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function PipelineStep({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number
  color: string
}) {
  return (
    <div className="flex flex-col items-center gap-2 min-w-[80px]">
      <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div className="text-center">
        <div className="text-lg font-semibold">{value}</div>
        <div className="text-xs text-apple-secondary">{label}</div>
      </div>
    </div>
  )
}
