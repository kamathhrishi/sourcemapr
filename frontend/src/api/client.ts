import type {
  Experiment,
  DashboardData,
  ParsedDocument,
  CreateExperimentRequest,
  UpdateExperimentRequest,
  AssignItemsRequest,
} from './types'

const BASE_URL = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  // Experiments
  async getExperiments(): Promise<Experiment[]> {
    return fetchJson<Experiment[]>(`${BASE_URL}/experiments`)
  },

  async createExperiment(data: CreateExperimentRequest): Promise<Experiment> {
    return fetchJson<Experiment>(`${BASE_URL}/experiments`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async updateExperiment(id: number, data: UpdateExperimentRequest): Promise<Experiment> {
    return fetchJson<Experiment>(`${BASE_URL}/experiments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  async deleteExperiment(id: number): Promise<void> {
    await fetchJson<{ status: string }>(`${BASE_URL}/experiments/${id}`, {
      method: 'DELETE',
    })
  },

  async assignToExperiment(experimentId: number, data: AssignItemsRequest): Promise<void> {
    await fetchJson<{ status: string }>(`${BASE_URL}/experiments/${experimentId}/assign`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async unassignFromExperiment(data: AssignItemsRequest): Promise<void> {
    await fetchJson<{ status: string }>(`${BASE_URL}/experiments/0/unassign`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // Dashboard data
  async getData(experimentId: number | null): Promise<DashboardData> {
    const url = experimentId
      ? `${BASE_URL}/data?experiment_id=${experimentId}`
      : `${BASE_URL}/data`
    return fetchJson<DashboardData>(url)
  },

  // Parsed documents (lazy loading)
  async getParsedDoc(docId: string): Promise<ParsedDocument> {
    return fetchJson<ParsedDocument>(`${BASE_URL}/parsed/${encodeURIComponent(docId)}`)
  },

  // Clear data
  async clearData(experimentId?: number, reset?: boolean): Promise<void> {
    let url = `${BASE_URL}/clear`
    const params = new URLSearchParams()
    if (experimentId) params.set('experiment_id', String(experimentId))
    if (reset) params.set('reset', 'true')
    if (params.toString()) url += `?${params}`

    await fetchJson<{ status: string }>(url, { method: 'POST' })
  },

  // File URL helper
  getFileUrl(filePath: string): string {
    return `${BASE_URL}/files/${encodeURIComponent(filePath)}`
  },
}
