# System architecture

## Components

- React + Vite frontend calls the FastAPI API with a short-lived bearer token.
- FastAPI authenticates users and scopes all library operations to the token
  subject.
- SQLAlchemy persists videos, source metadata, content records, model/version
  provenance, embeddings, and per-stage indexing states in PostgreSQL.
- Alembic's additive migration upgrades legacy tables while retaining their
  existing video and annotation data.
- Background indexing retrieves platform metadata and, only with explicit
  `owned`/`authorized` permission, may download remote media. Configured ASR,
  OCR, visual-caption, summary, and embedding adapters record provenance and
  explicit unavailable/failure statuses.
- Retrieval combines evidence-based lexical, optional semantic, visual
  description, and platform-metadata channels. Weights are re-normalized across
  channels that have usable scores for a request.

## Data and trust boundaries

`videos` stores source metadata, ownership, permission state, and curator/user
annotation fields. `video_content` stores original transcript, OCR, visual
description, and cited model-derived records with source type, timestamps,
confidence, and model/version provenance. `embeddings` reference the content
record and model/modality that produced each vector.

The embedding-input allowlist is explicit: title, platform caption, and
completed extracted-content records only. Category labels and curation notes
are not passed to extraction, summarization, embeddings, or benchmark ranking.
User notes can be searched only through an explicit non-benchmark opt-in;
categories are never searched. The evaluation runner keeps judgments local and
compares IDs only after it receives ranked search results.

## Limitations

Semantic ranking requires a configured text embedding model and matching
indexed vectors. Visual retrieval searches extracted visual descriptions;
image-vector generation is not implemented. ASR, OCR, frame captioning, and
LLM summaries are optional providers and report unavailable states when not
installed/configured. No retrieval benchmark scores are claimed until a
separately curated judgment set is evaluated.
