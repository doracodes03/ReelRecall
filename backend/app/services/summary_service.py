import json
import requests
from typing import Any

from app.core.config import settings

SUMMARY_EVIDENCE_FIELDS = {
    "original_transcript",
    "translated_transcript",
    "frame_ocr",
    "visual_frame_description",
}


class SummaryService:
    """Optional OpenAI-compatible provider, supplied only with source evidence."""

    @staticmethod
    def _allowed_evidence(
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "source_field": item["source_field"],
                "text": item["text"],
                "timestamp_start": item.get("timestamp_start"),
                "confidence": item.get("confidence"),
            }
            for item in evidence
            if isinstance(item.get("id"), str)
            and item.get("source_field") in SUMMARY_EVIDENCE_FIELDS
            and isinstance(item.get("text"), str)
            and item["text"].strip()
        ]

    @staticmethod
    def build_prompt(
        metadata: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> str:
        allowed_metadata = {
            key: metadata[key]
            for key in ("title", "source_caption")
            if key in metadata
        }
        allowed_evidence = SummaryService._allowed_evidence(evidence)
        return (
            "Summarize this short video using only the provided evidence. "
            "Distinguish statements in platform metadata from observations in "
            "transcript/OCR/visual evidence. Do not infer unsupported facts. "
            "Return JSON with keys summary, summary_evidence_ids, and concepts. "
            "summary_evidence_ids must cite the supplied evidence IDs that support "
            "the summary. Each concept must include text and evidence_ids citing "
            "the supplied evidence IDs. "
            "Do not create a concept without a supporting evidence ID.\n"
            "PLATFORM METADATA (not verified video content):\n"
            f"{json.dumps(allowed_metadata, ensure_ascii=False)}\n"
            "EXTRACTED VIDEO EVIDENCE:\n"
            f"{json.dumps(allowed_evidence, ensure_ascii=False)}"
        )

    def summarize(
        self,
        metadata: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not settings.summary_model or not settings.summary_api_base:
            return None
        allowed_evidence = self._allowed_evidence(evidence)
        if not allowed_evidence:
            return None
        headers = {"Content-Type": "application/json"}
        if settings.summary_api_key:
            headers["Authorization"] = f"Bearer {settings.summary_api_key}"
        response = requests.post(
            f"{settings.summary_api_base.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": settings.summary_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON and cite evidence IDs.",
                    },
                    {
                        "role": "user",
                        "content": self.build_prompt(metadata, allowed_evidence),
                    },
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        result = json.loads(content)
        if not isinstance(result.get("summary"), str):
            raise ValueError("Summary provider returned no summary string")
        valid_ids = {item["id"] for item in allowed_evidence}
        summary_evidence_ids = [
            evidence_id
            for evidence_id in result.get("summary_evidence_ids", [])
            if evidence_id in valid_ids
        ]
        if result["summary"].strip() and not summary_evidence_ids:
            raise ValueError("Summary provider returned no valid evidence citations")
        concepts = []
        for item in result.get("concepts", []):
            evidence_ids = [
                evidence_id
                for evidence_id in item.get("evidence_ids", [])
                if evidence_id in valid_ids
            ]
            concept_text = item.get("text")
            if isinstance(concept_text, str) and concept_text.strip() and evidence_ids:
                concepts.append(
                    {"text": concept_text.strip(), "evidence_ids": evidence_ids}
                )
        return {
            "summary": result["summary"].strip(),
            "summary_evidence_ids": summary_evidence_ids,
            "concepts": concepts,
            "model_name": settings.summary_model,
            "model_version": body.get("model", settings.summary_model),
        }
