import json
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.embedding import Embedding
from app.models.video import Video
from app.models.video_content import VideoContent
from app.retrieval.explanations import Evidence, explain_match
from app.schemas.search import (
    RetrievalMode,
    SearchEvidence,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.embedding_service import EmbeddingService, is_searchable_content


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "the", "to", "was",
    "what", "when", "where", "which", "with", "you",
}
GRAM_QUANTITY_RE = re.compile(
    r"(?<!\w)(\d+)\s*(?:g|gm|gms|gram|grams)\b",
    re.IGNORECASE,
)
PROTEIN_QUANTITY_RE = re.compile(
    r"(?<!\w)(\d+)\s*g(?:\s+of)?\s+protein\b"
    r"|(?<!\w)protein\s+(?:contains?\s+)?(\d+)\s*g\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SearchDocument:
    video_id: str
    text: str
    source_type: str
    source_field: str
    timestamp_start: float | None
    is_metadata: bool = False
    content_record_id: str | None = None


def _tokens(text: str) -> set[str]:
    normalized = GRAM_QUANTITY_RE.sub(
        lambda match: f"{match.group(1)}g",
        text.casefold(),
    )
    return {
        token.casefold()
        for token in TOKEN_RE.findall(normalized)
        if len(token) > 1 and token.casefold() not in STOP_WORDS
    }


def _protein_quantity(text: str) -> int | None:
    match = PROTEIN_QUANTITY_RE.search(GRAM_QUANTITY_RE.sub(
        lambda item: f"{item.group(1)}g",
        text.casefold(),
    ))
    if match is None:
        return None
    return int(match.group(1) or match.group(2))


def _lexical_score(
    query_tokens: set[str],
    text: str,
    query_protein_quantity: int | None = None,
) -> float:
    if not query_tokens:
        return 0.0
    document_tokens = _tokens(text)
    if not document_tokens:
        return 0.0
    overlap = query_tokens & document_tokens
    if not overlap:
        return 0.0
    coverage = len(overlap) / len(query_tokens)
    precision = len(overlap) / len(document_tokens)
    score = coverage * (0.75 + 0.25 * math.sqrt(precision))

    if query_protein_quantity is not None:
        document_quantity = _protein_quantity(text)
        if (
            document_quantity is not None
            and document_quantity != query_protein_quantity
        ):
            return score * 0.35
        if document_quantity == query_protein_quantity:
            score = min(1.0, score + 0.4)
    return score


def _cosine(left: list[float], right: list[float]) -> float:
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    if a.shape != b.shape or not a.size:
        return -1.0
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0:
        return -1.0
    return float(np.dot(a, b) / denominator)


def _documents(
    videos: list[Video],
    contents: list[VideoContent],
    include_annotations: bool,
) -> list[SearchDocument]:
    docs: list[SearchDocument] = []
    for video in videos:
        if video.title:
            docs.append(
                SearchDocument(
                    video.id, video.title, "platform_metadata", "title", None, True
                )
            )
        if video.source_caption:
            docs.append(
                SearchDocument(
                    video.id,
                    video.source_caption,
                    "platform_metadata",
                    "source_caption",
                    None,
                    True,
                )
            )
        if include_annotations:
            for field_name in ("curation_notes",):
                value = getattr(video, field_name, None)
                if value:
                    docs.append(
                        SearchDocument(
                            video.id,
                            value,
                            "user_annotation",
                            field_name,
                            None,
                        )
                    )
        for field_name, value in (
            ("source_platform", video.source),
            ("creator_name", video.creator),
            (
                "duration_seconds",
                f"{video.duration} seconds" if video.duration is not None else None,
            ),
        ):
            if value:
                docs.append(
                    SearchDocument(
                        video.id,
                        str(value),
                        "platform_metadata",
                        field_name,
                        None,
                        True,
                    )
                )
        tags = (video.source_metadata or {}).get("tags", [])
        if isinstance(tags, list) and tags:
            docs.append(
                SearchDocument(
                    video.id,
                    " ".join(str(tag) for tag in tags),
                    "platform_metadata",
                    "source_tags",
                    None,
                    True,
                )
            )

    for content in contents:
        if not is_searchable_content(content):
            continue
        docs.append(
            SearchDocument(
                content.video_id,
                content.text,
                content.source_type,
                content.source_field,
                content.timestamp_start,
                content_record_id=content.id,
            )
        )
    return docs


def _allowed(document: SearchDocument, mode: RetrievalMode) -> bool:
    if mode == "metadata":
        return document.is_metadata
    if mode == "visual":
        return document.source_field == "visual_frame_description"
    if mode in {"lexical", "semantic"}:
        return not document.is_metadata
    return True


def search_videos(
    session: Session,
    request: SearchRequest,
    user_id: str,
) -> SearchResponse:
    started = time.perf_counter()
    warnings: list[str] = []
    semantic_enabled = request.mode in ("hybrid", "semantic", "visual")
    embedding_service = EmbeddingService()
    if semantic_enabled and not embedding_service.available:
        warning = "Semantic channel unavailable: no embedding model is configured."
        if request.mode == "semantic":
            raise HTTPException(status_code=503, detail=warning)
        warnings.append(warning)

    videos = session.query(Video).filter_by(user_id=user_id).all()
    by_id = {video.id: video for video in videos}
    if not by_id:
        if request.mode == "visual":
            warnings.append("No extracted visual descriptions are indexed.")
        return SearchResponse(
            query=request.query,
            mode=request.mode,
            results=[],
            warnings=warnings,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    include_annotations = request.include_user_annotations and not request.benchmark
    content_query = session.query(VideoContent).filter(
        VideoContent.video_id.in_(by_id),
        VideoContent.processing_status == "completed",
    )
    contents = content_query.all()
    docs = [
        document
        for document in _documents(videos, contents, include_annotations)
        if _allowed(document, request.mode)
    ]
    document_by_record_id = {
        document.content_record_id: document
        for document in docs
        if document.content_record_id
    }

    tokens = _tokens(request.query)
    query_protein_quantity = _protein_quantity(request.query)
    lexical_by_doc = [
        _lexical_score(tokens, document.text, query_protein_quantity)
        for document in docs
    ]
    content_lexical_by_video: dict[str, float] = defaultdict(float)
    metadata_by_video: dict[str, float] = defaultdict(float)
    content_evidence_by_video: dict[str, tuple[float, SearchDocument]] = {}
    metadata_evidence_by_video: dict[str, tuple[float, SearchDocument]] = {}
    for document, score in zip(docs, lexical_by_doc):
        if score <= 0:
            continue
        if document.is_metadata:
            metadata_by_video[document.video_id] = max(
                metadata_by_video[document.video_id], score
            )
            old = metadata_evidence_by_video.get(document.video_id)
            if old is None or score > old[0]:
                metadata_evidence_by_video[document.video_id] = (score, document)
            continue
        content_lexical_by_video[document.video_id] = max(
            content_lexical_by_video[document.video_id], score
        )
        old = content_evidence_by_video.get(document.video_id)
        if old is None or score > old[0]:
            content_evidence_by_video[document.video_id] = (score, document)

    semantic_by_video: dict[str, float] = {}
    model_name = embedding_service.model_name
    if semantic_enabled and embedding_service.available:
        try:
            query_vector = embedding_service.embed(request.query)
        except (RuntimeError, ValueError) as exc:
            if request.mode == "semantic":
                raise HTTPException(
                    status_code=503,
                    detail=f"Semantic search is unavailable: {exc}",
                ) from exc
            warnings.append(f"Semantic channel unavailable: {exc}")
        else:
            vectors = (
                session.query(Embedding)
                .filter(
                    Embedding.video_id.in_(by_id),
                    Embedding.model_name == model_name,
                    Embedding.modality == "text",
                    Embedding.content_record_id.isnot(None),
                )
                .all()
            )
            for vector in vectors:
                if vector.vector is None or not vector.content_record_id:
                    continue
                try:
                    vector_values = json.loads(vector.vector)
                except (TypeError, json.JSONDecodeError):
                    warnings.append(
                        f"Skipped malformed embedding {vector.id}."
                    )
                    continue
                matched_document = document_by_record_id.get(
                    vector.content_record_id
                )
                if matched_document is None:
                    continue
                if request.mode == "visual" and (
                    matched_document.source_field != "visual_frame_description"
                ):
                    continue
                raw_similarity = _cosine(query_vector, vector_values)
                if raw_similarity < 0.15:
                    continue
                similarity = (raw_similarity - 0.15) / 0.85
                semantic_by_video[vector.video_id] = max(
                    semantic_by_video.get(vector.video_id, 0.0), similarity
                )
                old_evidence = content_evidence_by_video.get(vector.video_id)
                if old_evidence is None or old_evidence[0] <= 0:
                    content_evidence_by_video[vector.video_id] = (
                        similarity,
                        matched_document,
                    )
            if request.mode == "semantic" and not semantic_by_video:
                warnings.append("No indexed content met the semantic similarity threshold.")
    if request.mode == "visual" and not any(
        document.source_field == "visual_frame_description" for document in docs
    ):
        warnings.append("No extracted visual descriptions are indexed.")

    channel_weights = {"lexical": 0.45, "semantic": 0.55}
    content_scores_by_channel: dict[str, dict[str, float]] = {}
    if request.mode in ("hybrid", "lexical", "visual"):
        content_scores_by_channel["lexical"] = dict(content_lexical_by_video)
    if request.mode in ("hybrid", "semantic", "visual"):
        content_scores_by_channel["semantic"] = semantic_by_video

    has_content_matches = any(
        scores
        for channel_scores in content_scores_by_channel.values()
        for scores in channel_scores.values()
        if scores > 0
    )
    if request.mode == "hybrid" and not has_content_matches and metadata_by_video:
        warnings.append(
            "No extracted-content matches; showing platform metadata matches instead. "
            "Check video indexing stages and confirm FFmpeg and media permission "
            "are configured before re-indexing."
        )

    ranking: list[tuple[float, str, list[str]]] = []
    for video_id in by_id:
        if request.mode == "metadata":
            score = metadata_by_video.get(video_id, 0.0)
            channels = ["metadata"] if score > 0 else []
        elif request.mode == "hybrid" and not has_content_matches:
            score = metadata_by_video.get(video_id, 0.0)
            channels = ["metadata"] if score > 0 else []
        else:
            matching_channels = {
                channel: values[video_id]
                for channel, values in content_scores_by_channel.items()
                if values.get(video_id, 0.0) > 0
            }
            weight_total = sum(channel_weights[name] for name in matching_channels)
            score = (
                sum(
                    channel_weights[name] * value
                    for name, value in matching_channels.items()
                )
                / weight_total
                if weight_total
                else 0.0
            )
            channels = list(matching_channels)
        if score > 0:
            ranking.append((score, video_id, channels))
    ranking.sort(key=lambda row: (-row[0], row[1]))

    results: list[SearchResult] = []
    for score, video_id, channels in ranking[: request.limit]:
        video = by_id[video_id]
        evidence_match = content_evidence_by_video.get(video_id)
        if (
            evidence_match is None
            and request.mode in {"metadata", "hybrid"}
            and not has_content_matches
        ):
            evidence_match = metadata_evidence_by_video.get(video_id)
        if evidence_match:
            evidence_document = evidence_match[1]
            evidence = SearchEvidence(
                source_type=evidence_document.source_type,
                source_field=evidence_document.source_field,
                excerpt=evidence_document.text[:500],
                timestamp_start=evidence_document.timestamp_start,
            )
            reason = explain_match(
                Evidence(
                    evidence_document.text,
                    evidence_document.source_type,
                    evidence_document.source_field,
                    evidence_document.timestamp_start,
                )
            )
        else:
            evidence = SearchEvidence(
                source_type="model_generated",
                source_field="semantic_similarity",
                excerpt="",
            )
            reason = "Ranked by semantic similarity to indexed content."
        results.append(
            SearchResult(
                video_id=video_id,
                title=video.title or "Untitled video",
                score=round(score, 6),
                match_reason=reason,
                highlights=[evidence.excerpt] if evidence.excerpt else [],
                evidence=evidence,
                channels=channels,
            )
        )

    return SearchResponse(
        query=request.query,
        mode=request.mode,
        results=results,
        warnings=warnings,
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
    )
