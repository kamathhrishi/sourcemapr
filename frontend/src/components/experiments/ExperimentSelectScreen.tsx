import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  FileText,
  Search,
  Cpu,
  ChevronRight,
  MoreHorizontal,
  RefreshCw,
  Database,
  Layers,
  Trash2,
  Sun,
  Moon,
  Zap
} from 'lucide-react'
import { useExperiments, useCreateExperiment, useDeleteExperiment } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { FrameworkBadge } from '@/components/common/FrameworkBadge'
import { useAppStore } from '@/store'

export function ExperimentSelectScreen() {
  const navigate = useNavigate()
  const { isDarkMode, toggleDarkMode } = useAppStore()
  const { data: experiments, isLoading, error, refetch } = useExperiments()
  const createExperiment = useCreateExperiment()
  const deleteExperiment = useDeleteExperiment()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const handleCreateExperiment = async () => {
    if (!newName.trim()) return
    await createExperiment.mutateAsync({ name: newName, description: newDescription || undefined })
    setNewName('')
    setNewDescription('')
    setShowCreateModal(false)
  }

  const handleDeleteExperiment = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this experiment?')) {
      await deleteExperiment.mutateAsync(id)
    }
  }

  const handleSelectExperiment = (experimentId: number | 'all') => {
    if (experimentId === 'all') {
      navigate('/experiment/all')
    } else {
      navigate(`/experiment/${experimentId}`)
    }
  }

  const filteredExperiments = experiments?.filter(exp =>
    exp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    exp.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Calculate totals
  const totals = experiments?.reduce((acc, exp) => ({
    docs: acc.docs + (exp.doc_count || 0),
    queries: acc.queries + (exp.retrieval_count || 0),
    llm: acc.llm + (exp.llm_count || 0),
  }), { docs: 0, queries: 0, llm: 0 }) || { docs: 0, queries: 0, llm: 0 }

  return (
    <div className="min-h-screen" style={{ background: 'var(--background)' }}>
      {/* Header */}
      <header className="border-b sticky top-0 z-10" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--accent)' }}>
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              SourcemapR
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleDarkMode}
              className="h-8 w-8"
            >
              {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
            <Button
              onClick={() => setShowCreateModal(true)}
              size="sm"
              className="h-8 text-xs font-medium"
              style={{ background: 'var(--accent)', color: 'white' }}
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              New Experiment
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Experiments', value: experiments?.length || 0, icon: Layers },
            { label: 'Documents', value: totals.docs, icon: FileText },
            { label: 'Queries', value: totals.queries, icon: Search },
            { label: 'LLM Calls', value: totals.llm, icon: Cpu },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="console-card p-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="stat-value">{value}</div>
                  <div className="stat-label">{label}</div>
                </div>
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--background-subtle)' }}
                >
                  <Icon className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Experiments Section */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            Experiments
          </h2>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
                style={{ color: 'var(--text-muted)' }}
              />
              <Input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 w-56 h-8 text-sm"
                style={{
                  background: 'var(--surface)',
                  borderColor: 'var(--border)',
                }}
              />
            </div>
            <Button
              variant="outline"
              size="icon"
              onClick={() => refetch()}
              className="h-8 w-8"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Experiments List */}
        <div className="console-card overflow-hidden">
          {/* Global View Row */}
          <div
            onClick={() => handleSelectExperiment('all')}
            className="flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors group"
            style={{ borderBottom: '1px solid var(--border)' }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--background-subtle)' }}
            >
              <Layers className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  All Experiments
                </span>
                <Badge variant="secondary" className="text-xs">Global</Badge>
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Aggregated view across all experiments
              </div>
            </div>
            <div className="flex items-center gap-6 text-xs" style={{ color: 'var(--text-muted)' }}>
              <span className="mono">{totals.docs} docs</span>
              <span className="mono">{totals.queries} queries</span>
              <span className="mono">{totals.llm} calls</span>
            </div>
            <ChevronRight
              className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ color: 'var(--text-muted)' }}
            />
          </div>

          {/* Experiment Rows */}
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center">
              <p className="text-sm" style={{ color: 'var(--error)' }}>Failed to load experiments</p>
            </div>
          ) : filteredExperiments && filteredExperiments.length > 0 ? (
            filteredExperiments.map((exp) => (
              <div
                key={exp.id}
                onClick={() => handleSelectExperiment(exp.id)}
                className="flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors group"
                style={{ borderBottom: '1px solid var(--border)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--accent-subtle)' }}
                >
                  <Database className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {exp.name}
                    </span>
                    {exp.framework && <FrameworkBadge framework={exp.framework} />}
                  </div>
                  {exp.description && (
                    <div className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                      {exp.description}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-6 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span className="mono">{exp.doc_count} docs</span>
                  <span className="mono">{exp.retrieval_count} queries</span>
                  <span className="mono">{exp.llm_count} calls</span>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={(e) => handleDeleteExperiment(exp.id, e as unknown as React.MouseEvent)}
                      className="text-red-600"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <ChevronRight
                  className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: 'var(--text-muted)' }}
                />
              </div>
            ))
          ) : (
            <div className="p-12 text-center">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3"
                style={{ background: 'var(--background-subtle)' }}
              >
                <Database className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
              </div>
              <h3 className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                {searchQuery ? 'No experiments found' : 'No experiments yet'}
              </h3>
              <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
                {searchQuery
                  ? 'Try adjusting your search'
                  : 'Create your first experiment to get started'}
              </p>
              {!searchQuery && (
                <Button
                  onClick={() => setShowCreateModal(true)}
                  size="sm"
                  className="h-8 text-xs"
                  style={{ background: 'var(--accent)', color: 'white' }}
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  Create Experiment
                </Button>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Create Experiment Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Experiment</DialogTitle>
            <DialogDescription>
              Create a new experiment to organize your RAG pipeline traces.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Production Pipeline"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description" className="text-sm">Description</Label>
              <Input
                id="description"
                placeholder="Optional description..."
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateExperiment}
              disabled={!newName.trim()}
              style={{ background: 'var(--accent)', color: 'white' }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
