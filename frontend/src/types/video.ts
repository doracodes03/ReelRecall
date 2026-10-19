export type VideoSource = 'youtube' | 'instagram';

export interface Video {
  id: string;
  title: string;
  url: string;
  source: VideoSource;
  creator: string;
  thumbnailUrl?: string;
  duration?: number | null;
  summary: string;
  transcript: string;
  visualDescription: string;
  tags: string[];
  savedAt: string;
  permissionStatus: 'unknown' | 'owned' | 'authorized';
  stageStatuses: Record<string, string>;
  status: 'indexed' | 'queued' | 'processing' | 'partial' | 'metadata_only' | 'failed' | 'pending' | 'error';
}
