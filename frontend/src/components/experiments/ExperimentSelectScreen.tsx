import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Beaker, FileText, Search, Cpu, Settings } from 'lucide-react'
import { useExperiments, useCreateExperiment, useDeleteExperiment } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { FrameworkBadge } from '@/components/common/FrameworkBadge'
import { useAppStore } from '@/store'

export function ExperimentSelectScreen() {
  const navigate = useNavigate()
  const { isDarkMode, toggleDarkMode } = useAppStore()
  const { data: experiments, isLoading, error } = useExperiments()
  const createExperiment = useCreateExperiment()
  const deleteExperiment = useDeleteExperiment()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showManageModal, setShowManageModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')

  const handleCreateExperiment = async () => {
    if (!newName.trim()) return
    await createExperiment.mutateAsync({ name: newName, description: newDescription || undefined })
    setNewName('')
    setNewDescription('')
    setShowCreateModal(false)
  }

  const handleDeleteExperiment = async (id: number) => {
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

  return (
    <div className="min-h-screen bg-apple-bg">
      {/* Header */}
      <header className="border-b border-apple-border bg-apple-card">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-apple-blue to-apple-purple flex items-center justify-center">
              <Beaker className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">SourcemapR</h1>
              <p className="text-xs text-apple-secondary">RAG Observability Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={toggleDarkMode}>
              {isDarkMode ? '☀️' : '🌙'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowManageModal(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Manage
            </Button>
            <Button size="sm" onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              New Experiment
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-2">Experiments</h2>
          <p className="text-apple-secondary">
            Select an experiment to view its RAG pipeline traces, or view all data across experiments.
          </p>
        </div>

        {/* All Experiments Card */}
        <Card
          className="mb-6 cursor-pointer hover:border-apple-blue/50 transition-colors"
          onClick={() => handleSelectExperiment('all')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-apple-tertiary flex items-center justify-center">
                  <Beaker className="w-5 h-5 text-apple-secondary" />
                </div>
                <div>
                  <CardTitle className="text-lg">All Experiments</CardTitle>
                  <CardDescription>View data across all experiments</CardDescription>
                </div>
              </div>
              <Badge variant="secondary">Global View</Badge>
            </div>
          </CardHeader>
        </Card>

        {/* Experiment Cards Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-32 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-16 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card className="border-apple-red/50">
            <CardContent className="py-8 text-center">
              <p className="text-apple-red">Failed to load experiments</p>
              <p className="text-sm text-apple-secondary mt-1">{String(error)}</p>
            </CardContent>
          </Card>
        ) : experiments && experiments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {experiments.map((exp) => (
              <Card
                key={exp.id}
                className="cursor-pointer hover:border-apple-blue/50 transition-colors"
                onClick={() => handleSelectExperiment(exp.id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{exp.name}</CardTitle>
                    {exp.framework && <FrameworkBadge framework={exp.framework} />}
                  </div>
                  {exp.description && (
                    <CardDescription className="line-clamp-2">{exp.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-apple-secondary">
                    <div className="flex items-center gap-1.5">
                      <FileText className="w-4 h-4" />
                      <span>{exp.doc_count} docs</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Search className="w-4 h-4" />
                      <span>{exp.retrieval_count} queries</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Cpu className="w-4 h-4" />
                      <span>{exp.llm_count} LLM</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Beaker className="w-12 h-12 mx-auto mb-4 text-apple-secondary" />
              <h3 className="text-lg font-medium mb-2">No experiments yet</h3>
              <p className="text-apple-secondary mb-4">
                Create your first experiment to start tracking RAG pipeline traces.
              </p>
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Experiment
              </Button>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Create Experiment Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Experiment</DialogTitle>
            <DialogDescription>
              Create a new experiment to organize your RAG pipeline traces.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="My Experiment"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                placeholder="A brief description..."
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateExperiment} disabled={!newName.trim()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage Experiments Modal */}
      <Dialog open={showManageModal} onOpenChange={setShowManageModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Manage Experiments</DialogTitle>
            <DialogDescription>View and delete experiments.</DialogDescription>
          </DialogHeader>
          <div className="py-4 max-h-96 overflow-y-auto">
            {experiments && experiments.length > 0 ? (
              <div className="space-y-2">
                {experiments.map((exp) => (
                  <div
                    key={exp.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-apple-border"
                  >
                    <div>
                      <div className="font-medium">{exp.name}</div>
                      {exp.description && (
                        <div className="text-sm text-apple-secondary">{exp.description}</div>
                      )}
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteExperiment(exp.id)}
                    >
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-apple-secondary py-8">No experiments to manage</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
