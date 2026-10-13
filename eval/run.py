import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from time import perf_counter

import httpx


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * value), len(ordered) - 1)
    return ordered[index]


async def run_case(
    client: httpx.AsyncClient, semaphore: asyncio.Semaphore, case: dict
) -> dict:
    async with semaphore:
        started = perf_counter()
        try:
            response = await client.post(
                "/v1/support/messages",
                json={"account_id": case["account_id"], "message": case["message"]},
            )
            client_latency_ms = (perf_counter() - started) * 1000
            response.raise_for_status()
            payload = response.json()
            returned_slugs = {citation["slug"] for citation in payload["citations"]}
            expected_slug = case["expected_citation"]
            state_correct = payload["state"] == case["expected_state"]
            citation_correct = expected_slug in returned_slugs
            return {
                "id": case["id"],
                "completed": state_correct and citation_correct,
                "citation_correct": citation_correct,
                "citation_precision": 1 / len(returned_slugs) if citation_correct else 0.0,
                "tool_failures": sum(
                    1 for tool_call in payload["tool_calls"] if not tool_call["success"]
                ),
                "client_latency_ms": round(client_latency_ms, 2),
                "server_latency_ms": payload["latency_ms"],
                "estimated_cost_usd": payload["estimated_cost_usd"],
                "error": None,
            }
        except Exception as exc:
            return {
                "id": case["id"],
                "completed": False,
                "citation_correct": False,
                "citation_precision": 0.0,
                "tool_failures": 1,
                "client_latency_ms": round((perf_counter() - started) * 1000, 2),
                "server_latency_ms": 0.0,
                "estimated_cost_usd": 0.0,
                "error": str(exc),
            }


async def benchmark(base_url: str, dataset: Path, concurrency: int) -> dict:
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    if len(cases) != 100:
        raise ValueError(f"benchmark requires exactly 100 cases, found {len(cases)}")

    limits = httpx.Limits(max_connections=concurrency)
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=10, limits=limits) as client:
        results = await asyncio.gather(
            *(run_case(client, semaphore, case) for case in cases)
        )

    latencies = [result["client_latency_ms"] for result in results]
    summary = {
        "run_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "requests": len(results),
        "task_completion_rate": round(
            sum(result["completed"] for result in results) / len(results), 4
        ),
        "citation_correctness": round(
            sum(result["citation_correct"] for result in results) / len(results), 4
        ),
        "citation_precision": round(
            fmean(result["citation_precision"] for result in results), 4
        ),
        "tool_failures": sum(result["tool_failures"] for result in results),
        "latency_ms": {
            "mean": round(fmean(latencies), 2),
            "p50": round(median(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
        },
        "average_cost_per_request_usd": round(
            fmean(result["estimated_cost_usd"] for result in results), 6
        ),
        "errors": sum(result["error"] is not None for result in results),
    }
    return {"summary": summary, "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the 100-request support benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--dataset", type=Path, default=Path("eval/cases.jsonl"))
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument(
        "--output", type=Path, default=Path("benchmark-results/latest.json")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(benchmark(args.base_url, args.dataset, args.concurrency))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
