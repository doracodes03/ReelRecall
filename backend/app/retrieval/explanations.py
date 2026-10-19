from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    text: str
    source_type: str
    source_field: str
    timestamp_start: float | None = None


def explain_match(evidence: Evidence) -> str:
    if evidence.source_type == "platform_metadata":
        source = "source metadata"
    elif evidence.source_type == "user_annotation":
        source = "your annotation"
    elif evidence.source_field == "original_transcript":
        source = "transcript"
    elif evidence.source_field == "frame_ocr":
        source = "on-screen text"
    elif evidence.source_field == "visual_frame_description":
        source = "visual description"
    else:
        source = evidence.source_field.replace("_", " ")
    timestamp = (
        f" at {evidence.timestamp_start:.1f}s"
        if evidence.timestamp_start is not None
        else ""
    )
    excerpt = evidence.text.strip()
    if len(excerpt) > 220:
        excerpt = f"{excerpt[:217].rstrip()}..."
    return f"Matched {source}{timestamp}: “{excerpt}”"


class Explanations:
    def explain(self, item: str) -> str:
        return explain_match(Evidence(item, "model_generated", "matched_evidence"))
