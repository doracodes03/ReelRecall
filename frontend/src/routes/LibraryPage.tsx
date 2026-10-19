import { useCallback, useEffect, useMemo, useState } from 'react';
import Button from '../components/common/Button';
import EmptyState from '../components/common/EmptyState';
import LoadingState from '../components/common/LoadingState';
import BulkReindexDialog from '../components/videos/BulkReindexDialog';
import SaveVideoDialog from '../components/videos/SaveVideoDialog';
import VideoFilters, { type VideoSourceFilter } from '../components/videos/VideoFilters';
import VideoGrid from '../components/videos/VideoGrid';
import { getVideos, reindexAllVideos, type BulkReindexResult } from '../services/videos';
import type { Video } from '../types/video';

const activeStatuses = new Set<Video['status']>(['queued', 'processing']);
const terminalStatuses = new Set<Video['status']>([
  'indexed',
  'partial',
  'metadata_only',
  'failed',
  'error',
]);

export default function LibraryPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [sourceFilter, setSourceFilter] = useState<VideoSourceFilter>('all');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [batch, setBatch] = useState<BulkReindexResult | null>(null);
  const [batchMessage, setBatchMessage] = useState('');

  const refreshLibrary = useCallback(async () => {
    const items = await getVideos();
    setVideos(items);
    setError('');
    return items;
  }, []);

  useEffect(() => {
    refreshLibrary()
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Unable to load your library.');
      })
      .finally(() => setLoading(false));
  }, [refreshLibrary]);

  const hasActiveIndexing = videos.some((video) => activeStatuses.has(video.status));

  useEffect(() => {
    if (!hasActiveIndexing) return undefined;
    const timer = window.setInterval(() => {
      refreshLibrary().catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Unable to refresh indexing status.');
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [hasActiveIndexing, refreshLibrary]);

  const batchVideos = useMemo(
    () => batch?.queued_video_ids
      .map((id) => videos.find((video) => video.id === id))
      .filter((video): video is Video => Boolean(video)),
    [batch, videos],
  );
  const batchCompleted = batchVideos?.filter((video) => terminalStatuses.has(video.status)).length ?? 0;
  const batchProcessing = batchVideos?.filter((video) => video.status === 'processing').length ?? 0;
  const batchQueued = batchVideos?.filter((video) => video.status === 'queued').length ?? 0;
  const batchFailed = batchVideos?.filter((video) => video.status === 'failed' || video.status === 'error').length ?? 0;

  useEffect(() => {
    if (!batch || batch.queued_count === 0 || batchCompleted !== batch.queued_count) return;
    setBatchMessage(
      `Re-indexing finished: ${batch.queued_count - batchFailed} finished, ${batchFailed} failed. Check each status; metadata-only means no searchable content was extracted.`,
    );
    setBatch((current) => current ? { ...current, queued_video_ids: [] } : current);
  }, [batch, batchCompleted, batchFailed]);

  const filteredVideos = useMemo(
    () => sourceFilter === 'all'
      ? videos
      : videos.filter((video) => video.source === sourceFilter),
    [sourceFilter, videos],
  );

  const handleBulkReindex = async () => {
    setError('');
    setBatchMessage('');
    setSubmitting(true);
    try {
      const result = await reindexAllVideos();
      setBatch(result);
      setBatchMessage(
        result.queued_count > 0
          ? `Request accepted: ${result.queued_count} videos queued${result.already_active_count ? `; ${result.already_active_count} already active` : ''}.`
          : result.total_count === 0
            ? 'Your library is empty; there were no videos to queue.'
            : `No new videos queued; ${result.already_active_count} are already queued or processing.`,
      );
      setVideos((current) => current.map((video) => (
        result.queued_video_ids.includes(video.id)
          ? {
            ...video,
            status: 'queued',
            stageStatuses: { ...video.stageStatuses, indexing: 'queued' },
          }
          : video
      )));
      setConfirmOpen(false);
      if (result.queued_count > 0) {
        try {
          await refreshLibrary();
        } catch (refreshError) {
          setError(refreshError instanceof Error ? refreshError.message : 'Request was accepted, but statuses could not refresh.');
        }
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to queue library re-indexing.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState />;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-5 rounded-3xl border border-[var(--rr-border)] bg-white/90 p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-7">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--rr-purple)]">Your collection</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[var(--rr-text)]">My Library</h1>
          <p className="mt-1 text-sm text-[var(--rr-muted)]">{videos.length} {videos.length === 1 ? 'video' : 'videos'} saved to your memory</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            disabled={!videos.length || submitting}
            onClick={() => {
              setBatchMessage('');
              setConfirmOpen(true);
            }}
          >
            <span aria-hidden="true">↻</span>
            Re-index all videos
          </Button>
          <SaveVideoDialog onSaved={refreshLibrary} />
          <Button
            variant="ghost"
            disabled={refreshing}
            onClick={async () => {
              setRefreshing(true);
              try {
                await refreshLibrary();
              } catch (requestError) {
                setError(requestError instanceof Error ? requestError.message : 'Unable to refresh your library.');
              } finally {
                setRefreshing(false);
              }
            }}
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}
      {batchMessage && <p role="status" className="rounded-xl border border-violet-200 bg-[var(--rr-lavender)] p-3 text-sm font-medium text-violet-950">{batchMessage}</p>}
      {batch && batch.queued_count > 0 && batch.queued_video_ids.length > 0 && (
        <section aria-label="Bulk re-index progress" className="rounded-2xl border border-[var(--rr-border)] bg-white p-4 shadow-sm sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <h2 className="font-bold text-[var(--rr-text)]">Library re-index progress</h2>
            <span className="text-[var(--rr-muted)]">{batchCompleted} of {batch.queued_count} finished</span>
          </div>
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--rr-lavender)]"
            role="progressbar"
            aria-label="Videos re-indexed"
            aria-valuemin={0}
            aria-valuemax={batch.queued_count}
            aria-valuenow={batchCompleted}
          >
            <div
              className="h-full rounded-full bg-[image:var(--rr-gradient)] transition-all"
              style={{ width: `${(batchCompleted / batch.queued_count) * 100}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-[var(--rr-muted)]">
            {batchQueued} queued · {batchProcessing} processing · {batchCompleted} finished · {batchFailed} failed
          </p>
        </section>
      )}

      {hasActiveIndexing && !batch && (
        <p role="status" className="rounded-xl border border-violet-200 bg-[var(--rr-lavender)] p-3 text-sm text-violet-950">
          Indexing is in progress. This library refreshes statuses automatically.
        </p>
      )}

      <VideoFilters value={sourceFilter} onChange={setSourceFilter} />
      {videos.length === 0 ? (
        <EmptyState title="Your library is ready for its first video" description="Save a YouTube Short or Instagram Reel to start building your personal memory index." />
      ) : filteredVideos.length === 0 ? (
        <EmptyState title="No videos for this platform" description="Choose another platform filter to see your saved videos." />
      ) : (
        <VideoGrid videos={filteredVideos} />
      )}

      <BulkReindexDialog
        open={confirmOpen}
        total={videos.length}
        busy={submitting}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleBulkReindex}
      />
    </section>
  );
}
