import { FileText, Search, Activity, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  activeTab: 'overview' | 'documents' | 'queries'
  onTabChange: (tab: 'overview' | 'documents' | 'queries') => void
}

const tabs = [
  { id: 'overview' as const, label: 'Overview', icon: Activity },
  { id: 'documents' as const, label: 'Documents', icon: FileText },
  { id: 'queries' as const, label: 'Queries', icon: Search },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside
      className="w-56 flex flex-col"
      style={{
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ background: 'var(--accent)' }}
          >
            <Zap className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            SourcemapR
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3">
        <div
          className="text-[10px] font-medium uppercase tracking-wider px-2 mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          Navigation
        </div>
        <ul className="space-y-0.5">
          {tabs.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => onTabChange(id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-left transition-all text-sm',
                )}
                style={{
                  background: activeTab === id ? 'var(--accent-subtle)' : 'transparent',
                  color: activeTab === id ? 'var(--accent)' : 'var(--text-secondary)',
                }}
                onMouseEnter={(e) => {
                  if (activeTab !== id) {
                    e.currentTarget.style.background = 'var(--surface-hover)'
                    e.currentTarget.style.color = 'var(--text-primary)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (activeTab !== id) {
                    e.currentTarget.style.background = 'transparent'
                    e.currentTarget.style.color = 'var(--text-secondary)'
                  }
                }}
              >
                <Icon
                  className="w-4 h-4"
                  style={{
                    color: activeTab === id ? 'var(--accent)' : 'var(--text-muted)',
                  }}
                />
                <span className="font-medium">{label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="text-[11px] text-center" style={{ color: 'var(--text-muted)' }}>
          RAG Observability
        </div>
      </div>
    </aside>
  )
}
