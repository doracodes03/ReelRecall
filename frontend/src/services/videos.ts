import { fetchJson } from './api';
import type { Video, VideoSource } from '../types/video';

interface ApiVideo {
  id: string;
  title: string;
  url: string;
  source: VideoSource;
  creator: string | null;
  duration: number | null;
  thumbnail_url: string | null;
  summary?: string | null;
  transcript?: string | null;
  visual_description?: string | null;
  saved_at: string;
  status: string;
  permission_status: 'unknown' | 'owned' | 'authorized';
  stage_statuses: Record<string, string>;
}

interface ApiContent {
  content_type: string;
  content_text: string;
  timestamp_start: number | null;
}

function mapVideo(item: ApiVideo, contents: ApiContent[] = []): Video {
  return {
    id: item.id,
    title: item.title || 'Indexing video metadata...',
    url: item.url,
    source: item.source,
    creator: item.creator || 'Unknown creator',
    duration: item.duration,
    thumbnailUrl: item.thumbnail_url || undefined,
    summary: item.summary || contents
      .filter((content) => content.content_type === 'summary')
      .map((content) => content.content_text)
      .join('\n'),
    transcript: item.transcript || contents
      .filter((content) => content.content_type === 'transcript')
      .map((content) => content.content_text)
      .join('\n'),
    visualDescription: item.visual_description || contents
      .filter((content) => content.content_type === 'visual_description')
      .map((content) => content.content_text)
      .join('\n'),
    tags: [],
    savedAt: item.saved_at,
    permissionStatus: item.permission_status,
    stageStatuses: item.stage_statuses ?? {},
    status: item.status as Video['status'],
  };
}

export async function getVideos(): Promise<Video[]> {
  const items = await fetchJson<ApiVideo[]>('/videos');
  return items.map((item) => mapVideo(item));
}

export async function getVideoById(id: string): Promise<Video | undefined> {
  try {
    const item = await fetchJson<ApiVideo>(`/videos/${encodeURIComponent(id)}`);
    const contents = await fetchJson<ApiContent[]>(`/videos/${encodeURIComponent(id)}/content`);
    return mapVideo(item, contents);
  } catch (error) {
    if (error instanceof Error && error.message === 'Video not found') return undefined;
    throw error;
  }
}

export function saveVideo(
  url: string,
  permissionStatus: 'unknown' | 'owned' | 'authorized' = 'unknown',
): Promise<ApiVideo> {
  return fetchJson<ApiVideo>('/videos', {
    method: 'POST',
    body: JSON.stringify({ url, permission_status: permissionStatus }),
  });
}

export function reindexVideo(id: string): Promise<ApiVideo> {
  return fetchJson<ApiVideo>(`/videos/${encodeURIComponent(id)}/reindex`, {
    method: 'POST',
  });
}

export interface BulkReindexResult {
  total_count: number;
  queued_count: number;
  already_active_count: number;
  queued_video_ids: string[];
}

export function reindexAllVideos(): Promise<BulkReindexResult> {
  return fetchJson<BulkReindexResult>('/videos/reindex-all', {
    method: 'POST',
  });
}
