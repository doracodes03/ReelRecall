# Retrieval evaluation

Keep query wording and relevance judgments in a private, versioned evaluation
file separate from `dataset/manifest.csv`. Never add judgments to video
annotations or indexing inputs.

Use one JSON object per line:

```json
{"query_id":"memory-001","query":"the short explaining how a stack uses LIFO","relevant_video_ids":["video-uuid"]}
```

Run the evaluator with an access token for the account containing the judged
videos:

```powershell
$env:REELRECALL_TOKEN = "<access token>"
python scripts\evaluate_retrieval.py --queries evaluation\my-queries.jsonl --mode hybrid
```

The evaluator sends only each query, retrieval mode, and `benchmark: true` to
the API. Relevant video IDs are kept locally and compared against returned
rankings. It reports Recall@5/10, Precision@5/10, MRR@10, nDCG@10,
zero-result rate, and end-to-end mean/p95 latency. Precision@K uses K as the
denominator, including when fewer than K results are returned. There are no
benchmark judgments in this repository, so no retrieval-quality score is
claimed.

Relevance metrics measure ranking quality; they do not prove that indexing is
working. To report operational coverage (completed extracted-content records,
stage outcomes, and content-linked vectors for the configured model), run
`python -m app.cli.report_metrics` from `backend/`. The report excludes video
titles, URLs, and user IDs.
