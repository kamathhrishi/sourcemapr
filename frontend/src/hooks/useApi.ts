import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { CreateExperimentRequest, UpdateExperimentRequest, AssignItemsRequest } from '@/api/types'

// Query keys
export const queryKeys = {
  experiments: ['experiments'] as const,
  data: (expId: number | null) => ['data', expId] as const,
  parsedDoc: (docId: string) => ['parsed', docId] as const,
}

// Experiments
export function useExperiments() {
  return useQuery({
    queryKey: queryKeys.experiments,
    queryFn: () => api.getExperiments(),
  })
}

export function useCreateExperiment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateExperimentRequest) => api.createExperiment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments })
    },
  })
}

export function useUpdateExperiment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateExperimentRequest }) =>
      api.updateExperiment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments })
    },
  })
}

export function useDeleteExperiment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteExperiment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.experiments })
    },
  })
}

// Dashboard data with auto-refresh
export function useDashboardData(experimentId: number | null) {
  return useQuery({
    queryKey: queryKeys.data(experimentId),
    queryFn: () => api.getData(experimentId),
    refetchInterval: 3000, // Auto-refresh every 3 seconds
    staleTime: 1000,
  })
}

// Parsed document (lazy loading)
export function useParsedDocument(docId: string | null) {
  return useQuery({
    queryKey: queryKeys.parsedDoc(docId!),
    queryFn: () => api.getParsedDoc(docId!),
    enabled: !!docId,
    staleTime: Infinity, // Parsed docs don't change
  })
}

// Clear data
export function useClearData() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ experimentId, reset }: { experimentId?: number; reset?: boolean }) =>
      api.clearData(experimentId, reset),
    onSuccess: () => {
      queryClient.invalidateQueries()
    },
  })
}

// Assign items
export function useAssignItems() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ experimentId, data }: { experimentId: number; data: AssignItemsRequest }) =>
      api.assignToExperiment(experimentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries()
    },
  })
}

export function useUnassignItems() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AssignItemsRequest) => api.unassignFromExperiment(data),
    onSuccess: () => {
      queryClient.invalidateQueries()
    },
  })
}
