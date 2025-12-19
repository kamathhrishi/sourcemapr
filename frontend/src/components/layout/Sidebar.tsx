import { LayoutDashboard, FileText, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarProps {
  activeTab: 'overview' | 'documents' | 'queries'
  onTabChange: (tab: 'overview' | 'documents' | 'queries') => void
}

const tabs = [
  { id: 'overview' as const, label: 'Overview', icon: LayoutDashboard },
  { id: 'documents' as const, label: 'Documents', icon: FileText },
  { id: 'queries' as const, label: 'Queries', icon: Search },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-56 border-r border-apple-border bg-apple-card flex flex-col">
      {/* Logo */}
      <div className="h-14 border-b border-apple-border flex items-center px-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-apple-blue to-apple-purple flex items-center justify-center">
            <span className="text-white text-sm font-bold">S</span>
          </div>
          <span className="font-semibold">SourcemapR</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3">
        <ul className="space-y-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => onTabChange(id)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeTab === id
                    ? 'bg-apple-blue text-white'
                    : 'text-apple-secondary hover:bg-apple-tertiary hover:text-apple-text'
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-apple-border">
        <div className="text-xs text-apple-secondary text-center">
          RAG Observability
        </div>
      </div>
    </aside>
  )
}
