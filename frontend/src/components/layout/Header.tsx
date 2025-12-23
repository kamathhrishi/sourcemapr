import { useNavigate } from 'react-router-dom'
import { RefreshCw, Trash2, Moon, Sun, LayoutGrid, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FrameworkBadge } from '@/components/common/FrameworkBadge'
import { useAppStore } from '@/store'
import { useClearData } from '@/hooks/useApi'
import type { Experiment } from '@/api/types'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface HeaderProps {
  experimentId: number | null
  experiments: Experiment[]
  framework: string | null
  onRefresh: () => void
}

export function Header({ experimentId, experiments, framework, onRefresh }: HeaderProps) {
  const navigate = useNavigate()
  const { isDarkMode, toggleDarkMode, setExperiment } = useAppStore()
  const clearData = useClearData()

  const experiment = experiments.find((e) => e.id === experimentId)
  const experimentName = experiment?.name ?? 'All Experiments'

  const handleClear = async () => {
    if (confirm('Are you sure you want to clear all trace data? This cannot be undone.')) {
      await clearData.mutateAsync({ experimentId: experimentId ?? undefined })
      onRefresh()
    }
  }

  const handleExperimentSelect = (expId: number | null) => {
    setExperiment(expId)
    if (expId === null) {
      navigate('/experiment/all')
    } else {
      navigate(`/experiment/${expId}`)
    }
  }

  return (
    <header
      className="h-11 flex items-center px-3 gap-2"
      style={{
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {/* Back to Experiments Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate('/')}
        className="h-7 w-7 p-0"
        style={{ color: 'var(--text-secondary)' }}
        title="Back to Experiments"
      >
        <LayoutGrid className="w-4 h-4" />
      </Button>

      <div className="w-px h-4" style={{ background: 'var(--border)' }} />

      {/* Experiment Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 gap-1.5 font-medium"
            style={{ color: 'var(--text-primary)' }}
          >
            <span className="text-sm truncate max-w-[200px]">{experimentName}</span>
            {framework && <FrameworkBadge framework={framework} />}
            <ChevronDown className="w-3.5 h-3.5 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuItem
            onClick={() => handleExperimentSelect(null)}
            className={experimentId === null ? 'bg-accent/10' : ''}
          >
            <span className="font-medium">All Experiments</span>
          </DropdownMenuItem>
          {experiments.length > 0 && <DropdownMenuSeparator />}
          {experiments.map((exp) => (
            <DropdownMenuItem
              key={exp.id}
              onClick={() => handleExperimentSelect(exp.id)}
              className={experimentId === exp.id ? 'bg-accent/10' : ''}
            >
              <div className="flex items-center justify-between w-full">
                <span className="truncate">{exp.name}</span>
                {exp.framework && (
                  <span className="text-xs text-muted-foreground ml-2">{exp.framework}</span>
                )}
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <div className="flex-1" />

      {/* Actions */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          className="h-7 px-2 text-xs gap-1"
          style={{ color: 'var(--text-secondary)' }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="h-7 px-2 text-xs gap-1"
          style={{ color: 'var(--text-muted)' }}
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear
        </Button>
        <div className="w-px h-4 mx-0.5" style={{ background: 'var(--border)' }} />
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleDarkMode}
          className="h-7 w-7"
          style={{ color: 'var(--text-secondary)' }}
        >
          {isDarkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </Button>
      </div>
    </header>
  )
}
