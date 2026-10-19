# API documentation

All routes except `GET /health`, `GET /`, and account creation/login require
`Authorization: Bearer <access_token>`. A token is issued by `/auth/register` or
`/auth/login`; it expires after the configured `ACCESS_TOKEN_EXPIRE_MINUTES`.
Video, extracted-content, search, and library queries are scoped to the
authenticated user.

## Authentication

- `POST /auth/register` — body `{ "email", "full_name", "password" }`; returns a bearer token and user. Passwords must contain at least 12 characters.
- `POST /auth/login` — body `{ "email", "password" }`; returns a bearer token and user.
- `GET /auth/me` — return the current user.

Set a strong, private `JWT_SECRET` of at least 32 characters before using these
routes. Tokens use HS256 and password hashes use PBKDF2-HMAC-SHA256.

## Videos

- `GET /videos` — list only the current user's saved videos.
- `POST /videos` — validate, canonicalize, and save a supported HTTPS YouTube or Instagram video URL immediately; indexing runs asynchronously.
- `GET /videos/{video_id}` — get a saved video belonging to the current user.
- `GET /videos/{video_id}/content` — view provenance-aware extracted records.
- `POST /videos/{video_id}/reindex` — re-run indexing and generate vectors using the currently configured model.
- `DELETE /videos/{video_id}` — delete the current user's video and its content and embeddings.
- `GET /library/stats` — current user's library counts.

`POST /videos` accepts optional `manual_category`, `curation_notes`, and
`permission_status` (`unknown`, `owned`, or `authorized`). Media downloads are
attempted only for `owned` or `authorized`. A failed indexing stage does not
discard the saved URL; stage errors/statuses remain on the video record.

## Search

`POST /search` accepts:

```json
{
  "query": "a tutorial showing a linked list reversal",
  "limit": 10,
  "mode": "hybrid",
  "benchmark": true,
  "include_user_annotations": false
}
```

Supported modes are `hybrid`, `lexical`, `semantic`, `visual`, and `metadata`.
The response contains ranked results, actual matched evidence/source fields,
timestamps when available, active channels, warnings for unavailable providers,
and server-side retrieval latency. Semantic mode returns HTTP 503 if no
embedding provider is configured; hybrid mode degrades to available channels
and reports the missing channel.

After configuring or changing an embedding model, re-index saved videos before
expecting semantic results. The details page provides a re-index action.

User annotations are excluded by default and always excluded when
`benchmark: true`; `manual_category` is never a retrieval field. Evaluation
queries send no relevance judgments to this API. See
[the evaluation instructions](../evaluation/README.md).
