import { FileText, Search, Beaker, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  activeTab: 'overview' | 'documents' | 'queries'
  onTabChange: (tab: 'overview' | 'documents' | 'queries') => void
}

const tabs = [
  { id: 'overview' as const, label: 'Pipeline Overview', icon: Activity, description: 'RAG flow & metrics' },
  { id: 'documents' as const, label: 'Documents', icon: FileText, description: 'Sources & chunks' },
  { id: 'queries' as const, label: 'Queries', icon: Search, description: 'Retrievals & LLM calls' },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-64 border-r border-apple-border bg-apple-card flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-apple-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-sm">
            <Beaker className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold">SourcemapR</div>
            <div className="text-xs text-apple-secondary">RAG Observability</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3">
        <div className="text-xs font-medium text-apple-secondary uppercase tracking-wider px-3 mb-3">
          Trace Explorer
        </div>
        <ul className="space-y-1">
          {tabs.map(({ id, label, icon: Icon, description }) => (
            <li key={id}>
              <button
                onClick={() => onTabChange(id)}
                className={cn(
                  'w-full flex items-start gap-3 px-3 py-3 rounded-lg text-left transition-all',
                  activeTab === id
                    ? 'bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 border border-orange-200 dark:border-orange-800'
                    : 'hover:bg-apple-tertiary'
                )}
              >
                <div className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
                  activeTab === id
                    ? 'bg-gradient-to-br from-orange-500 to-amber-600 text-white'
                    : 'bg-apple-tertiary text-apple-secondary'
                )}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className={cn(
                    'font-medium text-sm',
                    activeTab === id ? 'text-orange-700 dark:text-orange-400' : 'text-apple-text'
                  )}>
                    {label}
                  </div>
                  <div className="text-xs text-apple-secondary truncate">
                    {description}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Help */}
      <div className="p-4 border-t border-apple-border">
        <div className="text-xs text-apple-secondary text-center">
          Tracing RAG pipelines made simple
        </div>
      </div>
    </aside>
  )
}
