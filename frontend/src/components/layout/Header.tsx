import { useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Trash2, Moon, Sun } from 'lucide-react'
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
    if (confirm('Are you sure you want to clear all trace data for this experiment?')) {
      await clearData.mutateAsync({ experimentId: experimentId ?? undefined })
      onRefresh()
    }
  }

  return (
    <header className="h-14 border-b border-apple-border bg-apple-card flex items-center px-4 gap-4">
      {/* Back button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => navigate('/')}
        className="shrink-0"
      >
        <ArrowLeft className="w-4 h-4" />
      </Button>

      {/* Experiment name */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <h1 className="font-semibold truncate">{experimentName}</h1>
        {experimentId === null && (
          <Badge variant="secondary" className="shrink-0">
            Global
          </Badge>
        )}
        {framework && <FrameworkBadge framework={framework} small />}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <Button variant="ghost" size="icon" onClick={toggleDarkMode}>
          {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
        <Button variant="ghost" size="icon" onClick={onRefresh}>
          <RefreshCw className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClear}
          className="text-apple-red hover:text-apple-red"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </header>
  )
}
