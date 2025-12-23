// API Response Types

export interface Experiment {
  id: number
  name: string
  description: string | null
  framework: string | null
  doc_count: number
  retrieval_count: number
  llm_count: number
  created_at: string
}

export interface Document {
  doc_id: string
  filename: string
  file_path: string
  num_pages: number | null
  experiment_id: number | null
  timestamp: string
}

export interface ParsedDocument {
  doc_id: string
  text: string
  timestamp: string
}

export interface Chunk {
  chunk_id: string
  doc_id: string
  index: number
  text: string
  text_length: number
  page_number: number | null
  start_char_idx: number | null
  end_char_idx: number | null
  experiment_id: number | null
  metadata?: Record<string, unknown>
}

export interface RetrievalResult {
  chunk_id: string
  doc_id: string
  text: string
  score: number
  page_number: number | null
  start_char_idx?: number | null
  end_char_idx?: number | null
  metadata?: Record<string, unknown>
}

export interface Retrieval {
  id: number
  trace_id: string | null
  retrieval_id: string | null
  query: string
  results: RetrievalResult[]
  response: string | null
  num_results: number
  duration_ms: number
  experiment_id: number | null
  framework: string | null
  timestamp: string
}

export interface LLMCall {
  id: number
  trace_id: string | null
  retrieval_id: string | null
  model: string
  prompt: string | null
  input_type: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  duration_ms: number
  temperature: number | null
  max_tokens: number | null
  finish_reason: string | null
  status: string
  response: string
  messages?: Message[]
  tool_calls?: ToolCall[]
  function_call?: FunctionCall
  error?: string
  experiment_id: number | null
  framework: string | null
  timestamp: string
}

export interface Message {
  role: string
  content: string
}

export interface ToolCall {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
}

export interface FunctionCall {
  name: string
  arguments: string
}

export interface Trace {
  trace_id: string
  name: string
  start_time: string
  end_time: string | null
}

export interface Stats {
  total_documents: number
  total_chunks: number
  total_embeddings: number
  total_retrievals: number
  total_traces: number
  total_llm_calls: number
}

export interface DashboardData {
  traces: Record<string, Trace>
  documents: Record<string, Document>
  parsed: Record<string, ParsedDocument>
  chunks: Record<string, Chunk>
  retrievals: Retrieval[]
  llm_calls: LLMCall[]
  stats: Stats
  experiments: Experiment[]
}

// Request types
export interface CreateExperimentRequest {
  name: string
  description?: string
}

export interface UpdateExperimentRequest {
  name?: string
  description?: string
}

export interface AssignItemsRequest {
  trace_ids?: string[]
  doc_ids?: string[]
  retrieval_ids?: number[]
  llm_ids?: number[]
}
