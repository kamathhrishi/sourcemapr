import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  Beaker,
  FileText,
  Search,
  Cpu,
  ChevronRight,
  MoreHorizontal,
  RefreshCw,
  Database,
  Layers,
  Activity,
  Trash2,
  Sun,
  Moon
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
    <div className="min-h-screen bg-apple-bg">
      {/* Header */}
      <header className="border-b border-apple-border bg-apple-card sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-sm">
              <Beaker className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">SourcemapR</h1>
              <p className="text-xs text-apple-secondary">RAG Observability Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={toggleDarkMode}>
              {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
            <Button
              onClick={() => setShowCreateModal(true)}
              className="bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white shadow-sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Experiment
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-apple-card rounded-xl border border-apple-border p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <div className="text-2xl font-bold">{experiments?.length || 0}</div>
                <div className="text-xs text-apple-secondary">Experiments</div>
              </div>
            </div>
          </div>
          <div className="bg-apple-card rounded-xl border border-apple-border p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <div className="text-2xl font-bold">{totals.docs}</div>
                <div className="text-xs text-apple-secondary">Documents</div>
              </div>
            </div>
          </div>
          <div className="bg-apple-card rounded-xl border border-apple-border p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                <Search className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <div className="text-2xl font-bold">{totals.queries}</div>
                <div className="text-xs text-apple-secondary">Queries</div>
              </div>
            </div>
          </div>
          <div className="bg-apple-card rounded-xl border border-apple-border p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <div className="text-2xl font-bold">{totals.llm}</div>
                <div className="text-xs text-apple-secondary">LLM Calls</div>
              </div>
            </div>
          </div>
        </div>

        {/* Experiments Section */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold">Experiments</h2>
            <p className="text-sm text-apple-secondary">Select an experiment to explore its RAG pipeline traces</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-apple-secondary" />
              <Input
                type="text"
                placeholder="Search experiments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 w-64 bg-apple-card"
              />
            </div>
            <Button variant="outline" size="icon" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Experiments List */}
        <div className="bg-apple-card rounded-xl border border-apple-border overflow-hidden">
          {/* Global View Row */}
          <div
            onClick={() => handleSelectExperiment('all')}
            className="flex items-center gap-4 px-5 py-4 border-b border-apple-border hover:bg-apple-tertiary/50 cursor-pointer transition-colors group"
          >
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 flex items-center justify-center">
              <Layers className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold">All Experiments</span>
                <Badge variant="secondary" className="text-xs">Global</Badge>
              </div>
              <div className="text-sm text-apple-secondary">View aggregated traces across all experiments</div>
            </div>
            <div className="flex items-center gap-6 text-sm text-apple-secondary">
              <div className="flex items-center gap-1.5">
                <FileText className="w-4 h-4" />
                <span>{totals.docs}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Search className="w-4 h-4" />
                <span>{totals.queries}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Cpu className="w-4 h-4" />
                <span>{totals.llm}</span>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-apple-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>

          {/* Experiment Rows */}
          {isLoading ? (
            <div className="p-5 space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-11 w-11 rounded-xl" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center">
              <p className="text-red-500 mb-2">Failed to load experiments</p>
              <p className="text-sm text-apple-secondary">{String(error)}</p>
            </div>
          ) : filteredExperiments && filteredExperiments.length > 0 ? (
            filteredExperiments.map((exp) => (
              <div
                key={exp.id}
                onClick={() => handleSelectExperiment(exp.id)}
                className="flex items-center gap-4 px-5 py-4 border-b border-apple-border last:border-b-0 hover:bg-apple-tertiary/50 cursor-pointer transition-colors group"
              >
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-orange-100 to-amber-100 dark:from-orange-900/30 dark:to-amber-900/30 flex items-center justify-center">
                  <Database className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{exp.name}</span>
                    {exp.framework && <FrameworkBadge framework={exp.framework} />}
                  </div>
                  {exp.description && (
                    <div className="text-sm text-apple-secondary truncate">{exp.description}</div>
                  )}
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-1.5 text-apple-secondary">
                    <FileText className="w-4 h-4" />
                    <span className="font-medium text-apple-text">{exp.doc_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-apple-secondary">
                    <Search className="w-4 h-4" />
                    <span className="font-medium text-apple-text">{exp.retrieval_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-apple-secondary">
                    <Cpu className="w-4 h-4" />
                    <span className="font-medium text-apple-text">{exp.llm_count}</span>
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
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
                <ChevronRight className="w-5 h-5 text-apple-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            ))
          ) : (
            <div className="p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-apple-tertiary flex items-center justify-center mx-auto mb-4">
                <Database className="w-8 h-8 text-apple-secondary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">
                {searchQuery ? 'No experiments found' : 'No experiments yet'}
              </h3>
              <p className="text-apple-secondary mb-6 max-w-md mx-auto">
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Create your first experiment to start tracing your RAG pipeline'}
              </p>
              {!searchQuery && (
                <Button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white"
                >
                  <Plus className="w-4 h-4 mr-2" />
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
            <DialogTitle>Create New Experiment</DialogTitle>
            <DialogDescription>
              Create a new experiment to organize and track your RAG pipeline traces.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Experiment Name</Label>
              <Input
                id="name"
                placeholder="e.g., Production RAG Pipeline"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                placeholder="Brief description of this experiment..."
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
              className="bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white"
            >
              Create Experiment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
