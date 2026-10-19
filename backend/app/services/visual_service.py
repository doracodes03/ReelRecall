from pathlib import Path
import subprocess
import tempfile
from typing import Any

from app.core.config import settings
from app.utils.ffmpeg import find_ffmpeg


class VisualService:
    def describe_frames(self, media_path: Path) -> dict[str, Any]:
        if not settings.vision_model.strip():
            return {"status": "unsupported", "items": []}
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return {
                "status": "unsupported: FFmpeg executable not found",
                "items": [],
            }
        try:
            from transformers import pipeline
        except ImportError:
            return {"status": "unsupported", "items": []}

        descriptions = pipeline("image-to-text", model=settings.vision_model)
        items: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="reelrecall-visual-") as directory:
            pattern = str(Path(directory) / "frame-%02d.jpg")
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-i",
                    str(media_path),
                    "-vf",
                    "fps=1/10,scale=768:-2",
                    "-frames:v",
                    "6",
                    pattern,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for index, frame in enumerate(sorted(Path(directory).glob("frame-*.jpg"))):
                result = descriptions(str(frame), max_new_tokens=80)
                text = result[0].get("generated_text", "").strip()
                if text:
                    items.append({"text": text, "timestamp": float(index * 10)})
        return {"status": "completed" if items else "empty", "items": items}
