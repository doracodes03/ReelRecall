import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _dcg(relevant: set[str], ranking: list[str], k: int) -> float:
    return sum(
        1.0 / math.log2(rank + 1)
        for rank, video_id in enumerate(ranking[:k], start=1)
        if video_id in relevant
    )


def evaluate_case(ranking: list[str], relevant: set[str]) -> dict[str, float]:
    if not relevant:
        raise ValueError("Each evaluation query must have at least one relevant video ID")
    first_relevant = next(
        (rank for rank, video_id in enumerate(ranking[:10], start=1) if video_id in relevant),
        None,
    )
    ideal_hits = min(len(relevant), 10)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return {
        "recall_at_5": len(set(ranking[:5]) & relevant) / len(relevant),
        "recall_at_10": len(set(ranking[:10]) & relevant) / len(relevant),
        "precision_at_5": len(set(ranking[:5]) & relevant) / 5,
        "precision_at_10": len(set(ranking[:10]) & relevant) / 10,
        "mrr_at_10": 1.0 / first_relevant if first_relevant else 0.0,
        "ndcg_at_10": _dcg(relevant, ranking, 10) / ideal_dcg if ideal_dcg else 0.0,
        "zero_result": float(not ranking),
    }


def _read_queries(path: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if (
                not isinstance(case, dict)
                or not isinstance(case.get("query"), str)
                or not case["query"].strip()
                or not isinstance(case.get("relevant_video_ids"), list)
                or not all(isinstance(value, str) for value in case["relevant_video_ids"])
            ):
                raise ValueError(f"Invalid evaluation query format on line {line_number}")
            if not case["relevant_video_ids"]:
                raise ValueError(f"Missing judgments on line {line_number}")
            cases.append(case)
    if not cases:
        raise ValueError(f"No evaluation queries found in {path}")
    return cases


def _request_search(
    api_url: str,
    token: str,
    query: str,
    mode: str,
) -> tuple[list[str], float]:
    body = json.dumps(
        {
            "query": query,
            "limit": 10,
            "mode": mode,
            "benchmark": True,
            "include_user_annotations": False,
        }
    ).encode("utf-8")
    request = Request(
        f"{api_url.rstrip('/')}/search",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Search API request failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Search API returned an unexpected response shape")
    result_ids = [
        item["video_id"]
        for item in payload["results"]
        if isinstance(item, dict) and isinstance(item.get("video_id"), str)
    ]
    return result_ids, elapsed_ms


def run_evaluation(
    cases: list[dict[str, object]],
    api_url: str,
    token: str,
    mode: str,
) -> dict[str, object]:
    per_query: list[dict[str, object]] = []
    metric_rows: list[dict[str, float]] = []
    latencies: list[float] = []
    for case in cases:
        query = str(case["query"])
        relevant = set(cast(list[str], case["relevant_video_ids"]))
        ranking, latency_ms = _request_search(api_url, token, query, mode)
        metrics = evaluate_case(ranking, relevant)
        metric_rows.append(metrics)
        latencies.append(latency_ms)
        per_query.append(
            {
                "query_id": case.get("query_id"),
                **metrics,
                "latency_ms": round(latency_ms, 3),
            }
        )
    keys = (
        "recall_at_5",
        "recall_at_10",
        "precision_at_5",
        "precision_at_10",
        "mrr_at_10",
        "ndcg_at_10",
        "zero_result",
    )
    return {
        "mode": mode,
        "query_count": len(cases),
        "aggregate": {
            key: statistics.mean(row[key] for row in metric_rows) for key in keys
        },
        "latency_ms_mean": statistics.mean(latencies),
        "latency_ms_p95": sorted(latencies)[
            max(0, int(0.95 * len(latencies) + 0.999) - 1)
        ],
        "per_query": per_query,
        "judgments_sent_to_search": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval without sending relevance judgments to the API."
    )
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument(
        "--mode",
        choices=("hybrid", "lexical", "semantic", "visual", "metadata"),
        default="hybrid",
    )
    args = parser.parse_args()
    token = os.environ.get("REELRECALL_TOKEN", "").strip()
    if not token:
        parser.error("Set REELRECALL_TOKEN to a valid user access token")
    result = run_evaluation(_read_queries(args.queries), args.api_url, token, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
