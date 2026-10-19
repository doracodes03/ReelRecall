import VideoCard from './VideoCard';
import type { Video } from '../../types/video';

export default function VideoGrid({ videos }: { videos: Video[] }) {
  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      {videos.map((video) => (
        <VideoCard key={video.id} video={video} />
      ))}
    </div>
  );
}
