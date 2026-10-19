import os
import shutil
from pathlib import Path

from app.core.config import settings


def find_ffmpeg() -> str | None:
    configured_path = settings.ffmpeg_path.strip()
    if configured_path:
        candidate = Path(configured_path).expanduser()
        if candidate.is_dir():
            candidate = candidate / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not candidate.is_file():
            raise FileNotFoundError(
                f"FFMPEG_PATH does not point to an FFmpeg executable: {candidate}"
            )
        return str(candidate.resolve())

    executable = shutil.which("ffmpeg")
    if executable:
        return executable

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            candidates = sorted(
                packages.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for candidate in candidates:
                if candidate.is_file():
                    return str(candidate.resolve())
    return None
