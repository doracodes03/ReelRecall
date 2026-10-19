import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import EmptyState from '../components/common/EmptyState';
import LoadingState from '../components/common/LoadingState';
import SaveVideoDialog from '../components/videos/SaveVideoDialog';
import VideoGrid from '../components/videos/VideoGrid';
import { getVideos } from '../services/videos';
import type { Video } from '../types/video';

const exampleQueries = [
  'A Python tutorial explaining how to remove duplicates.',
  'A high-protein paneer recipe without onion.',
  'A beige outfit with wide-leg trousers.',
  'A Hindi tutorial explaining SQL joins.',
];

export default function HomePage() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  const refreshLibrary = async () => {
    const items = await getVideos();
    setVideos(items);
    setError('');
  };

  useEffect(() => {
    refreshLibrary()
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Unable to load your videos.');
      })
      .finally(() => setLoading(false));
  }, []);

  const openSearch = (value = query) => {
    const searchQuery = value.trim();
    if (!searchQuery) {
      navigate('/search');
      return;
    }
    navigate('/search', { state: { query: searchQuery } });
  };

  return (
    <section className="space-y-10">
      <div className="relative overflow-hidden rounded-[2rem] border border-[var(--rr-border)] bg-white p-5 shadow-sm sm:p-8 lg:p-10">
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-28 size-80 rounded-full bg-[var(--rr-lavender)] blur-3xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-40 right-1/4 size-72 rounded-full bg-[var(--rr-blush)] blur-3xl" />
        <div className="relative max-w-4xl">
          <p className="inline-flex items-center gap-2 rounded-full bg-[var(--rr-blush)] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.14em] text-[var(--rr-magenta)]">
            <span className="size-2 rounded-full bg-[var(--rr-pink)]" />
            Your personal video memory
          </p>
          <h1 className="mt-5 max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight text-[var(--rr-text)] sm:text-5xl lg:text-6xl">
            Find the video <span className="bg-[image:var(--rr-gradient)] bg-clip-text text-transparent">you remember.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--rr-muted)] sm:text-lg">
            Search your saved Reels and Shorts by the scene, recipe, outfit, or words you remember — not just the exact title.
          </p>

          <form
            className="mt-7 flex max-w-3xl flex-col gap-3 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault();
              openSearch();
            }}
          >
            <label htmlFor="discover-query" className="sr-only">Describe the video you remember</label>
            <input
              id="discover-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Describe the Reel or Short you're trying to find..."
              className="min-h-14 min-w-0 flex-1 rounded-2xl border border-[var(--rr-border)] bg-white/95 px-5 py-4 text-base text-[var(--rr-text)] shadow-sm placeholder:text-[var(--rr-muted)] focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
            />
            <button
              type="submit"
              className="min-h-14 rounded-2xl bg-[image:var(--rr-gradient)] px-8 text-base font-bold text-white shadow-lg shadow-purple-900/15 transition hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0"
            >
              Search memory
            </button>
          </form>

          <div className="mt-5">
            <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--rr-muted)]">Try a memory prompt</p>
            <div className="flex flex-wrap gap-2">
              {exampleQueries.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setQuery(example);
                    openSearch(example);
                  }}
                  className="min-h-10 rounded-full border border-[var(--rr-border)] bg-white/90 px-4 py-2 text-left text-xs font-medium text-[var(--rr-muted)] transition hover:border-[var(--rr-purple)]/40 hover:bg-[var(--rr-lavender)] hover:text-[var(--rr-purple)] sm:text-sm"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-4 border-t border-[var(--rr-border)] pt-6">
            <SaveVideoDialog onSaved={refreshLibrary} />
            <span className="text-sm text-[var(--rr-muted)]">Save a Short or Reel to start building your library.</span>
          </div>
        </div>
      </div>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}

      <section aria-labelledby="recent-videos-title" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--rr-purple)]">Picked up where you left off</p>
            <h2 id="recent-videos-title" className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--rr-text)]">Recently saved</h2>
          </div>
          {videos.length > 0 && (
            <button
              type="button"
              onClick={() => navigate('/library')}
              className="min-h-10 rounded-full px-4 text-sm font-bold text-[var(--rr-purple)] transition hover:bg-[var(--rr-lavender)]"
            >
              View all {videos.length} →
            </button>
          )}
        </div>
        {loading ? <LoadingState /> : videos.length > 0 ? (
          <VideoGrid videos={videos.slice(0, 3)} />
        ) : (
          <EmptyState title="Your saved videos will live here" description="Add a Reel or Short, then search by anything you remember about it." />
        )}
      </section>
    </section>
  );
}
