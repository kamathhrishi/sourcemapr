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
  html_start_idx: number | null
  html_end_idx: number | null
  prev_anchor: string | null
  next_anchor: string | null
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
  html_start_idx?: number | null
  html_end_idx?: number | null
  prev_anchor?: string | null
  next_anchor?: string | null
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
  evaluations: Evaluation[]
  categories: QueryCategory[]
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

// Pipeline types for advanced RAG tracking
export interface StageChunk {
  id: number
  stage_id: string
  chunk_id: string
  doc_id: string
  text: string
  input_rank: number | null
  output_rank: number | null
  input_score: number | null
  output_score: number | null
  source: string | null
  status: 'kept' | 'filtered' | 'new'
}

export interface PipelineStage {
  id: number
  stage_id: string
  pipeline_id: string
  stage_type: 'query_expansion' | 'retrieval' | 'reranking' | 'compression' | 'filtering' | 'merge'
  stage_name: string
  stage_order: number
  input_count: number
  output_count: number
  duration_ms: number
  metadata: Record<string, unknown>
  chunks: StageChunk[]
}

export interface Pipeline {
  id: number
  pipeline_id: string
  experiment_id: number | null
  query: string
  total_duration_ms: number | null
  num_stages: number
  retrieval_id: string | null
  llm_call_id: number | null
  created_at: string
  stages: PipelineStage[]
}

// Evaluation types for AI agent workspace
export interface Evaluation {
  id: number
  evaluation_id: string
  experiment_id: number | null
  retrieval_id: string | null
  evaluation_type: 'llm_judge' | 'category' | 'error_class'
  metric_name: string | null
  score: number | null
  reasoning: string | null
  category: string | null
  error_type: string | null
  metadata: Record<string, unknown>
  agent_name: string | null
  created_at: string
  updated_at: string
}

export interface QueryCategory {
  id: number
  retrieval_id: string
  category: string
  confidence: number | null
  metadata: Record<string, unknown>
  agent_name: string | null
  created_at: string
}

export interface CategorySummary {
  category: string
  count: number
  avg_confidence: number | null
}
