import { fetchJson } from './api';
import type { SearchRequest, SearchResponse } from '../types/search';

export async function searchVideos(payload: SearchRequest): Promise<SearchResponse> {
  return fetchJson<SearchResponse>('/search', {
    method: 'POST',
    body: JSON.stringify({ benchmark: true, ...payload }),
  });
}
