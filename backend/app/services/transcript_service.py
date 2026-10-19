from pathlib import Path
from typing import Any

from app.core.config import settings


class TranscriptService:
    """Optional faster-whisper provider preserving original segments and language."""

    def transcribe(self, media_path: Path) -> dict[str, Any]:
        if not settings.transcription_model.strip():
            return {"status": "unsupported", "segments": [], "language": None}
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return {"status": "unsupported", "segments": [], "language": None}

        model = WhisperModel(
            settings.transcription_model,
            device="cpu",
            compute_type="int8",
        )
        segments, info = model.transcribe(
            str(media_path),
            beam_size=5,
            vad_filter=True,
            word_timestamps=False,
        )
        results = [
            {
                "text": segment.text.strip(),
                "start": float(segment.start),
                "end": float(segment.end),
                "language": info.language,
            }
            for segment in segments
            if segment.text.strip()
        ]
        return {
            "status": "completed" if results else "empty",
            "segments": results,
            "language": info.language,
            "language_probability": float(info.language_probability),
        }
