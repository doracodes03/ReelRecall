from pathlib import Path
import subprocess
import tempfile
from typing import Any

from app.core.config import settings
from app.utils.ffmpeg import find_ffmpeg


class OCRService:
    def extract(self, media_path: Path) -> dict[str, Any]:
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return {
                "status": "unsupported: FFmpeg executable not found",
                "items": [],
            }
        try:
            import easyocr
        except ImportError:
            return {"status": "unsupported: EasyOCR is not installed", "items": []}

        languages = [item.strip() for item in settings.ocr_languages.split(",") if item.strip()]
        reader = easyocr.Reader(languages, gpu=False)
        unique_text: set[str] = set()
        items: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="reelrecall-frames-") as directory:
            pattern = str(Path(directory) / "frame-%04d.jpg")
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-i",
                    str(media_path),
                    "-vf",
                    "fps=1/5,scale=960:-2",
                    "-frames:v",
                    "48",
                    pattern,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for index, frame in enumerate(sorted(Path(directory).glob("frame-*.jpg"))):
                timestamp = float(index * 5)
                for _, text, confidence in reader.readtext(str(frame)):
                    clean_text = " ".join(str(text).split())
                    normalized = clean_text.casefold()
                    if not clean_text or normalized in unique_text:
                        continue
                    unique_text.add(normalized)
                    items.append(
                        {
                            "text": clean_text,
                            "timestamp": timestamp,
                            "confidence": float(confidence),
                        }
                    )
        return {"status": "completed" if items else "empty", "items": items}
