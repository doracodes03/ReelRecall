# Product spec

## Problem and goal

People save short-form videos but later remember scenes, spoken explanations,
on-screen text, or context rather than exact titles and hashtags. ReelRecall
provides a private, per-user video library searchable by the evidence available
from each saved item.

## Core workflow

1. Register or sign in to a private account.
2. Save a supported video URL; the record is persisted before indexing starts.
3. Index platform metadata and, when locally available or explicitly
   authorized for download, transcript/OCR/visual-description evidence.
4. Search with hybrid, lexical, semantic, visual-description, or metadata mode.
5. Review ranked results with the matched field and timestamp when available.

## Data and trust requirements

- Keep videos and extracted content isolated by user ownership.
- Preserve original source evidence, model provenance, timestamps, confidence,
  and stage failures.
- Never use curator categories or evaluation judgments as extraction,
  embedding, or benchmark-ranking input.
- Treat platform descriptions as metadata, not verified content.
- Download remote media only for content explicitly marked owned or authorized.
- Clearly report missing optional providers and avoid synthetic content or
  fabricated embeddings.

## Current scope

The API implements account registration/login, user-scoped library operations,
background indexing, hybrid retrieval, and evidence-based match explanations.
Retrieval quality remains unmeasured because no judged benchmark set is
provided. Visual retrieval currently searches text descriptions produced from
frames; image embedding and production-grade job queuing are not implemented.
