# Support Operations Agent

A small support backend that answers policy questions, looks up account context, and proposes
support tickets. Record changes require explicit approval.

The service exposes exactly three tools:

| Tool | Purpose | Writes data |
| --- | --- | --- |
| `policy_search` | Retrieve ranked policy passages with citations | No |
| `account_lookup` | Read plan and account status | No |
| `create_ticket` | Propose or create a support ticket | Yes, after approval |

## Run it

Requirements: Docker and Docker Compose.

```bash
docker compose up --build -d
curl http://localhost:8000/health
```

The container applies the database migration and loads idempotent sample data at startup. OpenAPI
documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Use the web app

Open [http://localhost:8000](http://localhost:8000) after the containers are running. The web
workspace lets you complete the full demo without entering API commands:

- select one of the seeded customer accounts;
- ask policy questions and inspect the source used for each answer;
- approve or reject proposed ticket creation;
- view the selected account's recent tickets;
- review benchmark results on the Evaluation screen; and
- inspect live dependencies and the three-tool workflow on the System screen.

Swagger at `/docs` remains available for backend development, but it is not the product interface.

Ask a policy question:

```bash
curl -s http://localhost:8000/v1/support/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "account_id": "acct_1001",
    "message": "Can I get a refund for a purchase from last week?"
  }'
```

Request an escalation:

```bash
curl -s http://localhost:8000/v1/support/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "account_id": "acct_1001",
    "message": "I was charged twice. Please create a ticket for a human agent."
  }'
```

The second response contains `proposed_action.id`. Nothing has been inserted into `tickets` yet.
Approve it explicitly:

```bash
curl -s -X POST http://localhost:8000/v1/approvals/ACTION_ID/approve
```

An approval is valid for 15 minutes and can be used once. It can also be rejected with
`POST /v1/approvals/ACTION_ID/reject`.

## Benchmark

The checked-in dataset contains 100 requests. With the stack running:

```bash
python -m eval.run \
  --base-url http://localhost:8000 \
  --dataset eval/cases.jsonl
```

The report includes task completion, citation correctness and precision, tool failures, mean/p50/p95
latency, and estimated cost per request. Results are written to
`benchmark-results/latest.json`.

The checked-in local baseline in `eval/baseline.json` was produced with concurrency 10:

| Metric | Result |
| --- | ---: |
| Requests | 100 |
| Task completion | 100% |
| Citation correctness | 100% |
| Citation precision | 100% |
| Tool failures | 0 |
| Client latency p50 / p95 | 38.36 ms / 255.98 ms |
| Estimated model cost per request | $0.00 |

This is a deterministic, labeled development set, not a production claim. A production evaluation
should include paraphrases, stale policies, adversarial requests, and injected dependency failures.

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

The most important test proves that a ticket is not written when it is proposed, that approval
creates it once, and that replaying the same approval fails.

## Project layout

```text
app/                  API, orchestration, repositories, and tools
migrations/           PostgreSQL schema and full-text GIN index
scripts/seed.py       Idempotent accounts and support policies
eval/cases.jsonl      Fixed 100-request evaluation set
eval/run.py           Concurrent benchmark runner
tests/                Agent, retrieval, approval, and metric tests
docs/                 Design notes and interview walkthrough
```

See [docs/design.md](docs/design.md) for the request path and failure behavior, and
[docs/interview-guide.md](docs/interview-guide.md) for a concise explanation and demo script.
