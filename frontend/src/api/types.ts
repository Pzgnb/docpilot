export type KnowledgeBase = {
  id: string
  name: string
  description: string
  document_count: number
  created_at: string
  updated_at: string
}

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export type KnowledgeDocument = {
  id: string
  knowledge_base_id: string
  filename: string
  media_type: string
  status: DocumentStatus
  chunk_count: number
  error_code: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type Citation = {
  chunk_id: string
  document_id: string
  file_name: string
  content: string
}

export type ChatResponse = {
  answer: string
  decision: 'answer' | 'insufficient_context'
  citations: Citation[]
  retrieval_trace_id: string
  created_at: string
}

export type RetrievalHit = {
  chunk_id: string
  knowledge_base_id: string
  document_id: string
  file_name: string
  content: string
  vector_score: number
  keyword_score: number
  fusion_score: number
  rerank_score: number | null
  initial_rank: number
  final_rank: number
}

export type RetrievalTrace = {
  query: string
  knowledge_base_id: string
  rerank_status: 'not_configured' | 'applied'
  hits: RetrievalHit[]
}

export type EvaluationCase = {
  id: string
  knowledge_base_id: string
  question: string
  expected_decision: 'answer' | 'insufficient_context'
  expected_file_name: string | null
  required_keywords: string[]
  expected_top_rank: number
  expected_citation_ids: string[]
  created_at: string
}

export type EvaluationResult = {
  case_id: string | null
  passed: boolean
  error_type: 'none' | 'not_retrieved' | 'ranked_too_low' | 'answer_omission' | 'wrong_citation' | 'wrong_refusal'
  message: string
  retrieval_trace_id: string
}

export type EvaluationRun = {
  id: string
  knowledge_base_id: string
  total: number
  passed: number
  pass_rate: number
  results: EvaluationResult[]
  created_at: string
}
