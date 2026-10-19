# Evaluation plan

Use a versioned query/judgment file kept separate from the dataset manifest
and annotation columns. Each entry contains a query ID, the natural-language
query, and relevant video IDs. The evaluator sends only the query and
`benchmark: true` to the API; judgments remain local for metric computation.

Report macro-averaged:

- Recall@5 and Recall@10
- Precision@5 and Precision@10
- MRR@10
- binary-gain nDCG@10
- zero-result rate
- end-to-end mean and p95 query latency

Also monitor indexing/operational coverage separately from relevance quality:

- Percentage of saved videos with at least one completed, allowlisted content record
- Per-stage completed/failed/unsupported/skipped/queued counts
- Percentage of content-bearing videos with at least one active embedding for the configured model
- Semantic readiness (configured model plus active content-linked vectors)

Run `python -m app.cli.report_metrics` from `backend/` to produce a JSON
snapshot of library/indexing/embedding coverage. It reports no titles, URLs, or
user IDs.

Evaluate hybrid, lexical, semantic, visual-description, and metadata modes
separately when their corresponding evidence/provider is available. Record
which providers/models were configured and the dataset/index version. Compare
systems against a fixed baseline on the same held-out query set; do not tune
against test judgments.

There is currently no labeled benchmark set in this repository. Therefore,
there are no measured retrieval metrics or evidence for quality improvements.
See [evaluation instructions](../evaluation/README.md) for the runner format.
