## How a request is handled

1. `account_lookup` checks the customer account and returns the plan and account status.
2. `policy_search` searches the policy table using PostgreSQL full-text search.
3. The response is composed from the highest-ranked policy passage and includes its citation.
4. If escalation is requested, `create_ticket` stores a proposed action in Redis instead of
   creating the ticket immediately.
5. Approval consumes the Redis entry and writes the ticket to PostgreSQL.

The Redis entry expires after 15 minutes. It is consumed with `GETDEL`, so the same approval cannot
be replayed to create duplicate tickets.

## Tools

| Tool | What it does | Writes data? |
| --- | --- | --- |
| `policy_search` | Retrieves ranked support policies | No |
| `account_lookup` | Reads the customer's plan and status | No |
| `create_ticket` | Proposes a ticket and creates it after approval | Yes |

Keeping the tool list small makes the permissions easy to understand. Only one tool can modify a
record, and that tool has an approval boundary.

## Evaluation

The evaluation set contains 100 requests across four areas: billing, account access, subscriptions,
and privacy. Twenty requests ask for escalation.

The saved local run produced:

| Metric | Result |
| --- | ---: |
| Requests | 100 |
| Task completion | 100% |
| Citation correctness | 100% |
| Citation precision | 100% |
| Tool failures | 0 |
| Client latency p50 | 38.36 ms |
| Client latency p95 | 255.98 ms |
| Model cost per request | $0.00 |

These numbers come from a fixed development set, so they should not be treated as production
performance. The benchmark is mainly there to catch regressions in routing, citations, tool calls,
and approval behavior.

To run it again:

```bash
python -m eval.run
```

The full result is written to `benchmark-results/latest.json`. The checked-in summary is in
`eval/baseline.json`.

## Tests

Build and run the isolated test image:

```bash
make test
make lint
```

The approval tests verify that proposing a ticket does not write to PostgreSQL, approval creates one
ticket, and trying to reuse the same approval fails.

## Project structure

```text
app/
  static/              Web interface
  agent.py             Request routing and response composition
  tools.py             The three tool implementations
  repositories.py      Database queries
  approvals.py         Redis approval storage
  main.py              FastAPI routes
migrations/            Database migration
scripts/seed.py        Sample accounts and policy data
eval/                   Dataset, runner, and saved baseline
tests/                  Unit tests
docs/                   Design notes and interview guide
```

More detail is available in [docs/design.md](docs/design.md). For a short project explanation and
demo order, see [docs/interview-guide.md](docs/interview-guide.md).

## Current limitations

- The sample accounts are not protected by authentication.
- Policy retrieval is full-text search rather than embedding-based hybrid search.
- Approval decisions are temporary Redis records, not a permanent audit log.
- The benchmark uses a controlled development set.

For a production version, I would add authentication and tenant checks first, followed by a durable
approval audit table, rate limiting, and a larger evaluation set built from real support traffic.