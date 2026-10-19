# ReelRecall project context

This file is the detailed, datewise engineering handoff for future work on
ReelRecall. It is intentionally separate from `README.md`, which remains the
project's public setup and showcase document. Update this file when behavior,
architecture, evaluation results, or important limitations change. Never copy
credentials or private evaluation judgments here.

## Project goal

ReelRecall is a personal library for saving short-video links/media, indexing
their content, and finding them with natural-language queries. Retrieval is
intended to use evidence extracted from the video (for example speech,
on-screen text, and visual descriptions), rather than relying only on platform
titles and captions.

## Current state (2026-10-14)

- The configured database contains 14 saved videos; 13 remain `metadata_only`
  and one is `partial` after the extraction test below.
- One video has seven completed searchable content records (five transcript
  segments and two visual descriptions); the other 13 have no extracted
  content yet.
- The database has 23 vectors for the configured multilingual model; seven are
  linked to searchable content records. Content-vector coverage is 100% for
  the one video with extracted content. Semantic search is ready, but
  library-wide coverage remains low.
- Older un-reindexed rows can still show queued or missing stage values. The
  SQLAlchemy JSON `stage_statuses` field now uses `MutableDict`, so new
  in-place updates persist. Re-indexing is not automatic after installing
  FFmpeg or changing permission; existing records need a re-index request.
- When an existing video is re-indexed, the indexing stage now transitions
  `queued` -> `processing` -> `completed`; the unexpected-error entrypoint
  records a failure instead of leaving it queued.
- The first semantic search in a fresh backend process previously loaded the
  Sentence Transformers model synchronously; a measured cold request took
  31.4 seconds. The FastAPI lifespan now warms the model during backend startup
  so this cost is paid before serving searches.
- A single 45g protein query sanity check ranked the intended paneer tikka
  salad first using metadata-only Hybrid fallback. This is one manually
  checked example, not a relevance benchmark or evidence of general search
  quality.
- A fresh Hybrid query for `Ashtami look` returned the tested Ashtami video at
  rank 1 using semantic similarity over its `visual_frame_description`.
  This is another single-query sanity check, not a benchmark.
- OCR remains unsupported because EasyOCR is not installed. Summary remains
  unsupported because no summary API provider is configured.

The current database counts below were collected with
`backend/app/cli/report_metrics.py` at `2026-10-14T06:01:35Z`. The tool emits
aggregate counts only; it does not print titles, URLs, or user IDs.

```json
{
  "library": {
    "saved_videos": 14,
    "video_status_counts": {
      "metadata_only": 13,
      "partial": 1
    }
  },
  "indexing": {
    "videos_with_completed_extracted_content": 1,
    "extracted_content_coverage_percent": 7.14,
    "completed_searchable_content_records": 7,
    "content_record_counts": {
      "visual_description:completed": 2,
      "transcript:completed": 5
    },
    "stage_outcomes": {
      "embedding": {
        "completed": 1
      },
      "indexing": {
        "queued": 1
      },
      "media": {
        "completed": 1
      },
      "metadata": {
        "completed": 1,
        "queued": 13
      },
      "ocr": {
        "unsupported": 1
      },
      "summary": {
        "unsupported": 1
      },
      "transcript": {
        "completed": 1
      },
      "visual": {
        "completed": 1
      }
    }
  },
  "embeddings": {
    "configured_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "all_vectors": 23,
    "vectors_linked_to_current_searchable_content": 7,
    "videos_with_content_vectors": 1,
    "content_vector_coverage_percent": 100.0,
    "model_counts": {
      "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 23
    },
    "semantic_search_ready": true
  }
}
```

The 100% content-vector coverage is only for the single video with extracted
content; library-wide content coverage is 7.14%.

## Architecture and important boundaries

- **Backend:** FastAPI application, SQLAlchemy persistence, and Alembic
  migrations under `backend/`.
- **Frontend:** browser UI under `frontend/`, including saved-video details,
  search, indexing status, and per-video re-index action.
- **Retrieval:** Hybrid search combines lexical and available semantic
  evidence. If content evidence is absent, metadata fallback is reported rather
  than presented as successful content search. When content is present, Hybrid
  ranking prefers content matches over metadata-only matches.
- **Indexing:** optional providers produce provenance-bearing content records
  for transcript/translation, OCR, visual description, summary, entity, or
  topic evidence; embedding vectors may be linked to those records.
- **Evaluation:** `scripts/evaluate_retrieval.py` computes ranking metrics
  locally from returned IDs and a separate local relevance file. Judgment IDs
  are not sent to the search endpoint or mixed into indexing inputs.
- **Provenance/leakage:** curator annotations and evaluation judgments must
  remain excluded from extraction and benchmark search/embeddings. Preserve
  the allowlisted source-field/content-type checks when adding evidence.
- **Dataset intake:** manifest import is under
  `backend/app/cli/import_dataset_manifest.py`. Dataset curator labels are
  useful for local analysis but are not retrieval ground truth or model
  evidence.

## File map

- `backend/app/retrieval/hybrid_search.py` — retrieval channels, evidence
  ranking, metadata fallback, and protein-quantity normalization/matching.
- `backend/app/services/indexing_service.py` — stage orchestration, evidence
  persistence, and indexing statuses.
- `backend/app/services/embedding_service.py` — model availability,
  searchable-content validation, and permitted embedding inputs.
- `backend/app/api/routes/videos.py` — saved-video API and single/bulk re-index
  endpoints.
- `frontend/src/routes/VideoDetailsPage.tsx` — video evidence/status view and
  re-index UI; API client is in `frontend/src/services/videos.ts`.
- `backend/app/cli/report_metrics.py` — aggregate operational coverage report.
- `scripts/evaluate_retrieval.py` — local-judgment relevance evaluator.
- `docs/EVALUATION_PLAN.md` and `evaluation/README.md` — metric and benchmark
  instructions.
- `README.md` — keep for concise user-facing setup/showcase material, not this
  engineering journal.

## Metrics

### Relevance quality

The evaluator reports macro-averaged metrics across the judged query set:

- **Recall@K:** relevant returned videos in the first K divided by all
  judgments for that query. Useful for coverage.
- **Precision@K:** relevant videos in the first K divided by K, even when fewer
  than K results were returned. Useful for top-result usefulness.
- **MRR@10:** reciprocal rank of the first relevant result, or zero if none
  occurs in the first 10.
- **nDCG@10:** normalized discounted cumulative gain with binary relevance;
  rewards relevant results appearing earlier.
- **Zero-result rate:** fraction of queries with no returned results.
- **Mean and p95 latency:** end-to-end API request latency measured by the
  evaluator.

Relevance metrics require a fixed, human-judged query set. Keep the query
wording and relevant IDs private and separate from the manifest; record the
dataset/index snapshot and provider/model configuration used for every
comparison. Compare modes and releases on the same held-out judgments.

### Operational coverage

Operational metrics diagnose whether retrieval has usable evidence; they do
not measure ranking quality:

- Saved-video counts by status.
- Fraction of saved videos with at least one completed, allowlisted content
  record.
- Searchable content-record counts by type and processing status.
- Per-stage outcome counts: completed, empty, failed, unsupported, skipped,
  queued, and pending.
- Number of vectors linked to currently searchable content for the configured
  model, and the fraction of content-bearing videos with such a vector.
- Semantic readiness: configured model plus at least one compatible,
  searchable-content-linked vector.

Run the reproducible aggregate report from `backend/`:

```powershell
python -m app.cli.report_metrics
```

Interpret a null coverage percentage as an undefined denominator, and inspect
stage outcomes alongside status/content counts. Do not infer modality success
from metadata embeddings or a configured model alone.

### Measured one-query sanity check (not a benchmark)

For the manually checked query `healthy recipe 45gm protein`, the intended
result was “45g Protein, 360 Calories | High-Protein Paneer Tikka Salad”.
In a controlled metadata-only Hybrid run, with the embedding provider
deliberately stubbed unavailable to exercise the lexical/metadata fallback,
the intended item ranked first out of six results:

| Metric | Value |
|---|---:|
| Queries | 1 |
| Recall@5 | 1.00 |
| Recall@10 | 1.00 |
| Precision@5 | 0.20 |
| Precision@10 | 0.10 |
| MRR@10 | 1.00 |
| Binary nDCG@10 | 1.00 |
| Zero-result rate | 0.00 |
| Local retrieval latency | approximately 10 ms |

The latency is a local retrieval measurement with the provider stubbed, not
end-to-end API latency. Scores are based on one intended relevant item and a
single query; they are only a regression sanity check. They do not establish
general relevance quality or successful semantic indexing.

## Datewise progress

### Earlier work — exact dates unavailable in retained history

- Addressed dataset downloader problems, including obtaining video/audio
  together, FFmpeg merging, retries, and manifest tracking. The retained
  history reports 43 dataset videos at one point; this should not be confused
  with the 14 saved-video records in the current configured database.
- Replaced demo APIs with persisted, authenticated, user-scoped video and
  search routes; added optional metadata/transcript/OCR/visual-description/
  summary/embedding providers, migration support, manifest import, UI
  integration, and retrieval evaluation.
- Added evidence provenance and safeguards to keep curator labels and
  evaluation judgments out of model inputs and benchmark retrieval.
- Validated earlier implementation with backend tests, frontend production
  build, a SQLite migration test, and an authenticated API-isolation test.

### 2026-10-12 — dataset evidence

- The later-inspected manifest contains download rows dated 2026-10-12. This
  is the evidence date recorded by the manifest, not a claim that every
  downloader change happened on this date.

### 2026-10-13 — semantic indexing configuration

- Investigated the report that semantic search was not happening. The UI
  identified that no embedding model was configured.
- Set a default multilingual Sentence Transformers embedding model, made blank
  environment values fall back to defaults, and added the model dependency.
- Added a per-video re-index endpoint/action and live indexing-stage status
  display. Verified the resolved model setting and frontend build; backend
  tests passed at that point.
- Transcription, vision, OCR, and summary remain independently configurable.

### 2026-10-13 — poor result for a protein-quantity query

- Inspected the current saved-video database. The intended 45g paneer salad and
  other records were metadata-only; no completed extracted content or
  content-linked embeddings existed.
- Updated Hybrid ranking to prioritize content evidence over metadata-only
  matches, make metadata fallback explicit, normalize gram variants
  (`45gm`, `45g`, `45 grams`), and boost/penalize results based on requested
  protein quantity. Added regression coverage for the salad-vs-wrap scenario.
- A controlled metadata-only test ranked the target first. This is the
  one-query sanity result above, not a broad benchmark.
- At that point, 19 backend tests and the frontend production build passed.

### 2026-10-13 — evaluation and handoff metrics

- Added Precision@5 and Precision@10 to the retrieval evaluator and its
  regression test. Precision uses K as denominator, even when the result list
  is shorter.
- Added `backend/app/cli/report_metrics.py` for aggregate library, stage,
  searchable-content, and configured-model embedding coverage; it omits
  titles, URLs, and user IDs.
- Updated `docs/EVALUATION_PLAN.md` and `evaluation/README.md` with operational
  coverage and precision metric guidance.
- Current aggregate snapshot: 14 saved videos; 0 with searchable extracted
  content; 14 configured-model vectors, 0 linked to searchable content;
  semantic readiness false.
- No private multi-query judged benchmark is present; do not publish a
  multi-query quality score.
- Investigated the stale queued stage outcomes after the report was shared.
  Root cause was in-place mutation of the SQLAlchemy JSON `stage_statuses`
  column without mutable tracking. Applied `MutableDict.as_mutable(JSON)` to
  `Video.stage_statuses` and added a persistence regression test. All 20
  focused backend tests pass.

### 2026-10-13 — diagnosing and fixing media extraction

- The search screenshot showed Hybrid falling back to platform metadata. An
  aggregate database check found all 14 videos lacked local media; 13 were
  explicitly marked `authorized`, and one was `unknown`.
- Runtime checks found FFmpeg missing from PATH, despite yt-dlp and configured
  faster-whisper/Transformers providers being installed. Installed FFmpeg
  Shared 9.0.2 via winget. Existing terminals and backend processes need a
  restart to inherit the PATH update.
- Re-indexed one explicitly authorized Ashtami video. Media download/merge
  succeeded and frame descriptions were created. The first transcription
  attempt exposed `TypeError: open() got an unexpected keyword argument
  'metadata_errors'` with faster-whisper 1.2.1 and PyAV 19.0.1.
- Declared faster-whisper and Transformers in `backend/requirements.txt` and
  constrained PyAV to `av>=11,<19`; installed PyAV 18.1.0. Transcription then
  succeeded on the saved media with five segments (language `bn`). Full
  re-index persisted five transcript segments and two visual descriptions,
  plus seven content-linked embeddings.
- OCR reports `unsupported` because EasyOCR is not installed; summary reports
  `unsupported` because no summary API provider is configured. These are
  separate from the repaired download/transcription path.
- Updated the Hybrid metadata-fallback warning to direct users to inspect
  indexing stages and confirm FFmpeg/media permission. Updated README setup
  guidance for Windows FFmpeg installation.
- Verified `Ashtami look` against the re-indexed account: the target ranked
  first of one result with the semantic channel and visual-description
  evidence. This is a smoke test, not an aggregate quality result.
- Latest operational report: 14 saved videos, one with extracted content
  (7.14% library coverage), seven content-linked vectors, semantic readiness
  true; 13 saved videos still need re-indexing.
- All 20 focused backend tests passed; Pylance showed no diagnostics in the
  changed Python files.

### 2026-10-14 — FFmpeg discovery and OCR status diagnosis

- Investigated the user's video detail output: the backend's `shutil.which`
  lookup could not see FFmpeg because winget had installed it in the user's
  package directory but the running VS Code/backend process had not inherited
  the updated PATH. This caused media download to fail, which in turn caused
  transcript/OCR/visual/summary stages to be skipped for unavailable media.
- Added `FFMPEG_PATH` configuration and shared FFmpeg discovery: explicit path,
  PATH lookup, then standard per-user winget package location on Windows. Wired
  it into media download, OCR, and visual frame extraction. This removes the
  dependency on restarting the existing shell for the standard winget install.
- Made the OCR stage report a specific `unsupported: EasyOCR is not installed`
  state when video media is available but its optional Python dependency is
  missing. In the reported run, OCR did not execute at all; it was skipped
  because the earlier media stage had failed.
- Updated README to document FFmpeg discovery and `FFMPEG_PATH`.
- Added a winget-path discovery regression test; all 21 focused backend tests
  passed. Pylance found no errors in changed code except its expected optional
  import diagnostic for uninstalled EasyOCR.
- The existing failed video must be re-indexed to retry its media download.
  OCR will then show the explicit missing-EasyOCR status unless that optional
  dependency is installed.

### 2026-10-14 — metrics follow-up

- Re-ran `python -m app.cli.report_metrics` from `backend/` at
  `2026-10-14T06:01:35Z` (11:31 local time, UTC+05:30).
- Counts are unchanged from the previous report: 14 saved videos; one with
  completed extracted content (7.14% library coverage); seven completed
  searchable records (five transcript segments and two visual descriptions);
  and seven content-linked vectors for that video. Semantic readiness remains
  true.
- Thirteen videos remain `metadata_only`. Their metadata stage still reports
  `queued`, and one indexing stage still reports `queued`; this report run
  only measures state and does not itself trigger or perform indexing.
- OCR and summary remain `unsupported` for the one processed video because
  their optional providers are not configured/installed. No new retrieval
  relevance measurements were produced.

### 2026-10-14 — queued indexing stages and cold-search latency

- Traced the 13 remaining `metadata_only` records: all have retrieved
  platform metadata, 12 have permission `authorized` and one is `unknown`, and
  none have a local media file. Their existing `metadata=queued` values are
  persisted stale states from before mutable JSON tracking was fixed. Changing
  permissions and installing FFmpeg do not themselves enqueue a new indexing
  run; re-index each authorized video explicitly. The unknown-permission video
  must remain unprocessed until authorization is confirmed.
- Found that `IndexingService.process()` updated metadata/media/extraction
  statuses but never changed the orchestration `indexing` status from queued.
  It now records `processing` at entry and `completed` after the final commit;
  the existing unexpected-error handler persists a failure. Added a regression
  assertion.
- Measured search in one fresh process: first Hybrid request took 31,355 ms
  while the model loaded; four subsequent requests took about 27–29 ms. The
  model loader is process-cached, so process restarts/cold starts reproduce
  the long first-request delay.
- Added FastAPI lifespan warm-up using a background thread: model loading and
  warm-up occur during startup, before serving searches. Verified warm-up plus
  three searches in a fresh process: startup warm-up 14,004 ms; searches
  91.9 ms, 32.5 ms, and 25.4 ms. These are local CPU measurements on the
  current DB, not a production latency SLO.
- Restricted semantic vector retrieval to text vectors linked to content
  records, avoiding unrelated title/caption vectors.
- Updated README startup guidance. All 20 focused backend tests passed;
  `pip check` reported no broken requirements and Pylance reported no
  diagnostics in changed Python files.

### 2026-10-14 — discovery UI and bulk re-indexing

- Reworked the authenticated React surfaces around a pink-purple-blue
  discovery theme: responsive navigation, the home search/discovery page,
  library filters/cards, video details, authentication, and the save-video
  dialog. Search example prompts use the existing search route/API; the UI
  does not fabricate search results.
- Added authenticated `POST /videos/reindex-all`. It is scoped to the current
  user, locks that user's video rows while choosing work, skips videos already
  queued/processing, returns the queued IDs/counts, and schedules the existing
  indexing pipeline sequentially. Unexpected per-video worker exceptions are
  logged and do not stop subsequent batch items. Existing media-permission
  checks remain in force.
- The library confirms before starting, reports active/already-queued counts,
  polls statuses while work is active, and exposes an accessible progress bar.
  Terminal `metadata_only` is described as a finished attempt without
  searchable extracted content, not as successful content extraction.
- Validation on this code revision: the focused backend suite passed 25 tests
  (`python -m unittest discover -s tests -p 'test_provenance_and_search.py'`
  from `backend/`); `npm run build` passed (`tsc -b` and Vite production
  build). The browser was unauthenticated, so authenticated pages and their
  interactive flows were not exercised end-to-end. At the browser's narrowest
  available viewport (400 px), the login page had no horizontal overflow.
- Re-ran `python -m app.cli.report_metrics` from `backend/` at
  `2026-10-14T07:30:29Z`. Current configured database snapshot:

  | Operational metric | Result |
  | --- | ---: |
  | Saved videos | 14 |
  | Video status | 10 `metadata_only`, 4 `partial` |
  | Videos with completed extracted content | 4 / 14 (28.57%) |
  | Completed searchable content records | 44 (27 OCR, 10 transcript, 7 visual descriptions) |
  | Content vectors linked to current searchable records | 44 |
  | Content-vector coverage among content-bearing videos | 100% |
  | Semantic search readiness | `true` |

  The report also counted 16 superseded transcript records and 60 total vectors
  across the configured model; neither number should be confused with current
  searchable evidence. This metrics command only reports stored state; it does
  not queue or run re-indexing.

### 2026-10-14 — metrics refresh

- Re-ran `python -m app.cli.report_metrics` from `backend/` at
  `2026-10-14T11:47:50Z` (17:17:50 local time, UTC+05:30).
- The snapshot is unchanged from the 07:30:29Z report: 14 saved videos (10
  `metadata_only`, 4 `partial`); 4 videos have completed extracted content
  (28.57%); 44 completed searchable records (27 OCR, 10 transcript, 7 visual
  descriptions); and 44 current searchable-content-linked vectors. Semantic
  search readiness is `true`, with 100% content-vector coverage among the
  four content-bearing videos.
- Stage counts remain 4 completed media stages, 3 completed indexing stages,
  1 queued indexing stage, 10 queued metadata stages, and 4 unsupported summary
  stages. OCR is completed for 3 videos and unsupported for 1; transcript is
  completed for 3 and empty for 1. The report is observational and does not
  enqueue work or refresh these statuses.

## Known issues and next actions

1. **Re-index remaining eligible videos.** Restart the backend process so it
   sees FFmpeg on PATH and runs model warm-up, then use the Library action for
   videos whose media permission is `owned` or `authorized`. Inspect unknown
   permission records and do not download their media unless authorization is
   confirmed.
2. **Enable OCR if needed.** Install EasyOCR in the selected environment and
   re-index to extract on-screen text. Configure a summary API only if
   evidence-grounded summaries are desired.
3. **Build a private, representative relevance set.** Include varied topics,
   quantities, languages, and queries with multiple relevant clips; report
   per-query and aggregate metrics on a held-out set before making quality
   claims.
4. **Retest end-to-end.** Run focused backend tests and frontend build after
   changes to indexing or retrieval; measure API latency with real configured
   providers separately from local search latency.

## Local setup notes and credential hygiene

- Run Alembic from the backend working directory so the `app` package is
  importable; the project configuration and migration environment live under
  `backend/`.
- Earlier PowerShell setup reported `docker` missing from PATH. Docker Compose
  is not required for the SQLite-backed local workflow, if that is the
  selected database configuration.
- An earlier `.env` terminal warning concerned VS Code terminal environment
  injection (`python.terminal.useEnvFile`); it is separate from application
  runtime configuration.
- A JWT signing secret was pasted into an earlier conversation. Rotate it
  before relying on that value; the secret itself is intentionally not
  recorded here.
