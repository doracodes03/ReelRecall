from pathlib import Path
import shutil
from typing import Any

import yt_dlp

from app.core.config import settings
from app.utils.ffmpeg import find_ffmpeg


class MetadataService:
    """Retrieve public platform metadata and download only explicitly authorized media."""

    def extract(self, url: str) -> dict[str, Any]:
        options: dict[str, Any] = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "extractor_retries": 2,
        }
        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("The platform returned no metadata")
        return info

    def download(self, url: str, external_video_id: str) -> Path:
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError(
                "FFmpeg is required to download merged audio/video; install it, "
                "add it to PATH, or set FFMPEG_PATH to ffmpeg.exe"
            )

        output_dir = Path(settings.data_dir)
        if not output_dir.is_absolute():
            output_dir = Path(__file__).resolve().parents[3] / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / f"{external_video_id}.%(ext)s")
        options: dict[str, Any] = {
            "format": (
                "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[height<=720]+bestaudio/best[acodec!=none]"
            ),
            "merge_output_format": "mp4",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 2,
            "fragment_retries": 5,
            "max_filesize": settings.max_video_size_mb * 1024 * 1024,
            "ffmpeg_location": ffmpeg,
        }
        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.extract_info(url, download=True)
        if not result:
            raise RuntimeError("The platform did not return a downloaded video")

        candidates = list(output_dir.glob(f"{external_video_id}.*"))
        media = [
            path
            for path in candidates
            if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
        ]
        if not media:
            raise RuntimeError("yt-dlp completed without producing a media file")
        return max(media, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def source_fields(info: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": info.get("title"),
            "source_caption": info.get("description"),
            "creator": info.get("uploader") or info.get("channel"),
            "duration": info.get("duration"),
            "thumbnail_url": info.get("thumbnail"),
            "published_at": info.get("upload_date"),
            "tags": info.get("tags") or [],
            "extractor": info.get("extractor_key") or info.get("extractor"),
        }
