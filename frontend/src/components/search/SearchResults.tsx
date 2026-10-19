import type { SearchResult } from '../../types/search';
import { Link } from 'react-router-dom';

export default function SearchResults({
  results,
  searched,
}: {
  results: SearchResult[];
  searched: boolean;
}) {
  if (!results.length) {
    return <p className="rounded-2xl border border-[var(--rr-border)] bg-white p-5 text-sm text-[var(--rr-muted)]">
      {searched ? 'No matching videos were found in your library.' : 'Search your saved videos by what you remember.'}
    </p>;
  }

  return (
    <div className="space-y-4">
      {results.map((result) => (
        <article key={result.video_id} className="rounded-2xl border border-[var(--rr-border)] bg-white p-4 shadow-sm sm:p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-[var(--rr-text)] sm:text-lg">
              <Link to={`/videos/${encodeURIComponent(result.video_id)}`} className="hover:text-[var(--rr-purple)]">{result.title}</Link>
            </h3>
            <span className="shrink-0 text-sm font-semibold text-[var(--rr-purple)]">{result.score.toFixed(2)} score</span>
          </div>
          <p className="mt-2 text-sm text-[var(--rr-muted)]">{result.match_reason}</p>
          {result.evidence.excerpt && (
            <blockquote className="mt-3 border-l-2 border-[var(--rr-purple)]/40 pl-3 text-sm text-[var(--rr-text)]">
              {result.evidence.excerpt}
              {result.evidence.timestamp_start !== null && (
                <span className="ml-2 text-xs text-[var(--rr-muted)]">
                  {result.evidence.timestamp_start.toFixed(1)}s
                </span>
              )}
            </blockquote>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {result.highlights.map((highlight) => (
              <span key={highlight} className="rounded-full bg-[var(--rr-lavender)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--rr-purple)]">{highlight}</span>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
