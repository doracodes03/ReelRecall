import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import SearchBar from '../components/search/SearchBar';
import SearchFilters from '../components/search/SearchFilters';
import SearchResults from '../components/search/SearchResults';
import { searchVideos } from '../services/search';
import type { RetrievalMode, SearchResponse } from '../types/search';

export default function SearchPage() {
  const location = useLocation();
  const [query, setQuery] = useState(
    typeof location.state?.query === 'string' ? location.state.query : '',
  );
  const [mode, setMode] = useState<RetrievalMode>('hybrid');
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setError('');
    setLoading(true);
    try {
      setResponse(await searchVideos({ query, mode }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Search failed.');
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--rr-purple)]">Search your collection</p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-[var(--rr-text)]">Find it from a fragment.</h1>
        <p className="mt-2 text-sm text-[var(--rr-muted)]">Describe a scene, a spoken phrase, or the topic you remember.</p>
      </div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} />
      <SearchFilters mode={mode} onChange={setMode} />
      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}
      {response?.warnings.map((warning) => (
        <p key={warning} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">{warning}</p>
      ))}
      {response && (
        <p className="text-xs text-[var(--rr-muted)]">
          {response.results.length} results · {response.latency_ms.toFixed(1)} ms
        </p>
      )}
      {loading ? <p role="status" className="text-sm text-[var(--rr-muted)]">Searching your library...</p> : (
        <SearchResults results={response?.results ?? []} searched={response !== null} />
      )}
    </section>
  );
}
