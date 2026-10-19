export type RetrievalMode = 'hybrid' | 'lexical' | 'semantic' | 'visual' | 'metadata';

export interface SearchEvidence {
  source_type: string;
  source_field: string;
  excerpt: string;
  timestamp_start: number | null;
}

export interface SearchResult {
  video_id: string;
  title: string;
  score: number;
  match_reason: string;
  highlights: string[];
  evidence: SearchEvidence;
  channels: string[];
}

export interface SearchRequest {
  query: string;
  limit?: number;
  mode?: RetrievalMode;
}

export interface SearchResponse {
  query: string;
  mode: RetrievalMode;
  results: SearchResult[];
  warnings: string[];
  latency_ms: number;
}
