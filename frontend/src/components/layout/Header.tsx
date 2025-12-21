import { useNavigate } from 'react-router-dom'
import { RefreshCw, Trash2, Moon, Sun, Layers, ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FrameworkBadge } from '@/components/common/FrameworkBadge'
import { useAppStore } from '@/store'
import { useClearData } from '@/hooks/useApi'
import type { Experiment } from '@/api/types'

interface HeaderProps {
  experimentId: number | null
  experiments: Experiment[]
  framework: string | null
  onRefresh: () => void
}

export function Header({ experimentId, experiments, framework, onRefresh }: HeaderProps) {
  const navigate = useNavigate()
  const { isDarkMode, toggleDarkMode } = useAppStore()
  const clearData = useClearData()

  const experiment = experiments.find((e) => e.id === experimentId)
  const experimentName = experiment?.name ?? 'All Experiments'

  const handleClear = async () => {
    if (confirm('Are you sure you want to clear all trace data? This cannot be undone.')) {
      await clearData.mutateAsync({ experimentId: experimentId ?? undefined })
      onRefresh()
    }
  }

  return (
    <header className="h-16 border-b border-apple-border bg-apple-card flex items-center px-6 gap-4">
      {/* Back Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate('/')}
        className="gap-1.5 text-apple-secondary hover:text-apple-text"
      >
        <ChevronLeft className="w-4 h-4" />
        Experiments
      </Button>

      <div className="w-px h-6 bg-apple-border" />

      {/* Experiment Info */}
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="w-10 h-10 rounded-lg bg-apple-tertiary flex items-center justify-center">
          <Layers className="w-5 h-5 text-apple-secondary" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="font-semibold text-lg truncate">{experimentName}</h1>
            {experimentId === null && (
              <Badge variant="secondary" className="shrink-0 text-xs">
                Global View
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-apple-secondary">
            {framework ? (
              <FrameworkBadge framework={framework} />
            ) : (
              <span>Viewing all framework traces</span>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleClear}
          className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30"
        >
          <Trash2 className="w-4 h-4" />
          Clear Data
        </Button>
        <div className="w-px h-6 bg-apple-border mx-1" />
        <Button variant="ghost" size="icon" onClick={toggleDarkMode}>
          {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
      </div>
    </header>
  )
}
