import { Link } from 'react-router-dom';
import type { Video } from '../../types/video';

const statusLabels: Record<Video['status'], string> = {
  indexed: 'Indexed',
  queued: 'Queued',
  processing: 'Processing',
  partial: 'Partially indexed',
  metadata_only: 'Metadata only',
  failed: 'Failed',
  pending: 'Pending',
  error: 'Error',
};

function formatDuration(duration?: number | null): string | null {
  if (duration == null || duration < 0) return null;
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

export default function VideoCard({ video }: { video: Video }) {
  const duration = formatDuration(video.duration);
  return (
    <Link
      to={`/videos/${video.id}`}
      className="group block overflow-hidden rounded-2xl border border-[var(--rr-border)] bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-xl hover:shadow-purple-950/10"
    >
      <div className="relative aspect-video overflow-hidden bg-[image:var(--rr-gradient)]">
        {video.thumbnailUrl ? (
          <img
            src={video.thumbnailUrl}
            alt=""
            loading="lazy"
            className="size-full object-cover transition duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="grid size-full place-items-center bg-[image:var(--rr-gradient)] text-5xl font-black text-white/90" aria-hidden="true">
            {video.source === 'youtube' ? '▶' : '◎'}
          </div>
        )}
        {duration && <span className="absolute bottom-3 right-3 rounded-md bg-black/75 px-2 py-1 text-xs font-semibold text-white">{duration}</span>}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--rr-purple)]">{video.source}</p>
            <h3 className="mt-1 line-clamp-2 text-base font-bold leading-6 text-[var(--rr-text)]">{video.title}</h3>
            <p className="mt-1 truncate text-sm text-[var(--rr-muted)]">{video.creator}</p>
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${
            video.status === 'indexed'
              ? 'bg-emerald-50 text-emerald-800'
              : video.status === 'failed' || video.status === 'error'
                ? 'bg-rose-50 text-rose-800'
                : video.status === 'processing' || video.status === 'queued'
                  ? 'bg-violet-50 text-violet-800'
                  : 'bg-amber-50 text-amber-900'
          }`}>{statusLabels[video.status] ?? video.status}</span>
        </div>
        <p className="mt-3 line-clamp-2 min-h-10 text-sm leading-5 text-[var(--rr-muted)]">
          {video.summary || video.transcript || video.visualDescription || 'Content is not indexed yet.'}
        </p>
        <p className="mt-3 border-t border-[var(--rr-border)] pt-3 text-xs text-[var(--rr-muted)]">
          Saved {new Date(video.savedAt).toLocaleDateString()}
        </p>
      </div>
    </Link>
  );
}
