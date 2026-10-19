import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import LoadingState from '../components/common/LoadingState';
import { getVideoById, reindexVideo } from '../services/videos';
import type { Video } from '../types/video';

function displayStageStatus(value: string): string {
  return value.replace(/[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*/g, 'local file');
}

export default function VideoDetailsPage() {
  const { id } = useParams();
  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reindexing, setReindexing] = useState(false);
  const [reindexMessage, setReindexMessage] = useState('');

  useEffect(() => {
    if (!id) return;
    getVideoById(id)
      .then((item) => {
        setVideo(item ?? null);
        if (!item) setError('Video not found.');
      })
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Unable to load this video.');
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id || !video || !['queued', 'processing'].includes(video.status)) return;

    const timer = window.setInterval(() => {
      getVideoById(id)
        .then((item) => {
          if (item) setVideo(item);
        })
        .catch((requestError: unknown) => {
          setError(requestError instanceof Error ? requestError.message : 'Unable to refresh indexing status.');
        });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [id, video?.status]);

  const handleReindex = async () => {
    if (!id) return;
    setError('');
    setReindexMessage('');
    setReindexing(true);
    try {
      const updated = await reindexVideo(id);
      setVideo((current) => current
        ? { ...current, status: updated.status as Video['status'], stageStatuses: updated.stage_statuses }
        : current);
      setReindexMessage('Re-indexing started. Existing evidence is retained while it runs.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to start re-indexing.');
    } finally {
      setReindexing(false);
    }
  };

  if (loading) return <LoadingState />;
  if (error && !video) return <p role="alert" className="text-sm text-rose-800">{error}</p>;
  if (!video) return null;

  return (
    <section className="space-y-6">
      <div className="rounded-3xl bg-[image:var(--rr-gradient)] p-6 text-white shadow-lg shadow-purple-950/10 sm:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/80">{video.source}</p>
        <h1 className="mt-3 text-2xl font-extrabold tracking-tight sm:text-3xl">{video.title}</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-2xl border border-[var(--rr-border)] bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-xl font-bold text-[var(--rr-text)]">Summary</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--rr-muted)]">{video.summary || 'No evidence-grounded summary is available yet.'}</p>

          <h2 className="mt-7 text-xl font-bold text-[var(--rr-text)]">Transcript</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--rr-muted)]">{video.transcript || 'No transcript is available yet.'}</p>

          <h2 className="mt-7 text-xl font-bold text-[var(--rr-text)]">Visual description</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--rr-muted)]">{video.visualDescription || 'No visual description is available yet.'}</p>
        </div>

        <div className="rounded-2xl border border-[var(--rr-border)] bg-white p-5 shadow-sm sm:p-6">
          <h3 className="text-lg font-bold text-[var(--rr-text)]">Video details</h3>
          <button
            type="button"
            disabled={reindexing}
            onClick={handleReindex}
            className="mt-4 min-h-11 rounded-xl bg-[image:var(--rr-gradient)] px-4 py-2.5 text-sm font-bold text-white transition hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reindexing ? 'Starting…' : 'Re-index video content'}
          </button>
          {reindexMessage && <p role="status" className="mt-2 text-sm text-emerald-800">{reindexMessage}</p>}
          {error && <p role="alert" className="mt-2 text-sm text-rose-800">{error}</p>}
          <ul className="mt-5 space-y-3 text-sm text-[var(--rr-muted)]">
            <li><strong>Index status:</strong> {video.status}</li>
            <li><strong>Media permission:</strong> {video.permissionStatus}</li>
            <li><strong>Creator:</strong> {video.creator}</li>
            <li><strong>Saved:</strong> {video.savedAt}</li>
            <li><strong>URL:</strong> <a className="break-all font-medium text-[var(--rr-purple)] underline" href={video.url} target="_blank" rel="noreferrer">{video.url}</a></li>
          </ul>
          <h4 className="mt-6 font-bold text-[var(--rr-text)]">Indexing stages</h4>
          <dl className="mt-3 space-y-2 border-t border-[var(--rr-border)] pt-3 text-xs text-[var(--rr-muted)]">
            {Object.entries(video.stageStatuses).map(([stage, stageStatus]) => (
              <div key={stage} className="flex items-start justify-between gap-3">
                <dt className="shrink-0 capitalize">{stage}</dt>
                <dd className="break-words text-right">{displayStageStatus(stageStatus)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
