# ReelRecall

ReelRecall is an AI-powered short-video memory and semantic search MVP for saving and rediscovering YouTube Shorts and Instagram Reels using natural-language memory recall instead of brittle manual tags.

## Highlights

- Save video URLs from YouTube Shorts and Instagram Reels
- Keep each user's saved videos and search results private
- Extract platform metadata, audio transcripts, on-screen text, and visual descriptions when providers are configured
- Search indexed evidence with lexical, optional semantic, visual-description, metadata, or hybrid retrieval
- Explain results using the matched source field and any available timestamp

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a fresh secret.
   For PowerShell:

   ```powershell
   $bytes = New-Object byte[] 32
   [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
   [Convert]::ToBase64String($bytes)
   ```

   Paste the generated value into `.env`. Do not use the example database
   password or commit `.env`.

2. Install the backend dependencies, start PostgreSQL, and migrate the existing schema:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
docker compose up -d db
cd backend
alembic upgrade head
```

The migration adds missing columns to the legacy `videos` table and creates
new provenance/indexing tables without deleting legacy data.

3. Start the API and frontend in separate terminals:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Create an account in the web app. Every video, search, and library operation
requires its bearer token and is scoped to that account. Saved links are stored
immediately; metadata and configured content-indexing stages run afterwards.
Remote media is downloaded only when its permission is explicitly marked
`owned` or `authorized`; local files can be indexed without a remote download.
Downloading/merging media requires FFmpeg on `PATH`. On Windows, install it
with `winget install --id Gyan.FFmpeg.Shared --exact`, then restart the backend
terminal so it inherits the updated `PATH`. The backend also discovers the
standard per-user winget installation; set `FFMPEG_PATH` to the full
`ffmpeg.exe` path if FFmpeg is installed elsewhere.

### Optional indexing providers

Semantic search uses the default multilingual
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` model. Install
backend requirements and start the backend with internet access so Sentence
Transformers can download and warm the model. The initial backend startup may
take longer; semantic searches then avoid the model's cold-load delay. Set
`EMBEDDING_MODEL` to a different Sentence Transformers model if needed. Use each video's
**Re-index for semantic search** action to create vectors for videos saved
before embeddings were configured. `TRANSCRIPTION_MODEL` uses faster-whisper;
`VISION_MODEL` uses Transformers for frame descriptions. FFmpeg must be
available for media download and frame extraction. OCR additionally requires
EasyOCR; its stage status explains when that optional dependency is missing.
Missing optional providers are recorded as unsupported stage statuses; the API
does not invent transcripts, descriptions, or vectors.

The Library page's **Re-index all videos** action queues only videos that are
not already queued or processing, and shows live per-video batch progress.
It remains scoped to the signed-in user's library and respects each video's
media permission. A `metadata_only` result means indexing finished without
searchable extracted content; check the per-stage status for the cause.

Import the existing dataset manifest into a specific account after creating
that account:

```powershell
python scripts\import_dataset_manifest.py --owner-email you@example.com
```

The importer preserves manifest category/notes as annotation fields, marks
license permission as unknown, and never sends those annotations to extraction
or benchmark ranking. Add `--index` to process imported entries immediately.

See [evaluation/README.md](./evaluation/README.md) for a judgment-isolated
retrieval evaluation workflow. No labeled evaluation set or measured quality
baseline is included in the repository.
## Product goals

This project is built as an MVP for a personal library of short-form videos, where a user can recall a video using memory, scene details, spoken explanation, mood, or metadata rather than exact title words.

## Repository structure

- `frontend/` — React + Vite + TypeScript app
- `backend/` — FastAPI API + retrieval services
- `docs/` — product, architecture, API, and evaluation specs
- `docker-compose.yml` — local orchestration for app services

## Dataset downloads

Install the Python dependencies, Node.js (for current YouTube extraction), and
FFmpeg (to merge separate audio and video streams). The downloader automatically
uses Node and searches for FFmpeg in PATH or the standard WinGet install location.

Run the configured URL list:

```powershell
python scripts\download_dataset.py
```

Retry only one configured URL while diagnosing a failure:

```powershell
python scripts\download_dataset.py --url "https://youtube.com/shorts/M3cFQzFyx1E?si=6IMbuRJnVxkhp0iy"
```

For Instagram Reels that require a logged-in session, use a browser profile where
you are already signed in:

```powershell
python scripts\download_dataset.py --cookies-from-browser chrome
```

The downloader saves per-URL outcomes and errors in `dataset/manifest.csv`.
Private, deleted, region-restricted, or otherwise inaccessible posts still
require legitimate access; the downloader cannot retrieve unavailable media.
