# Interview guide

## Two-minute explanation

This service handles common support questions and escalations. Every request first verifies the
account, then retrieves relevant policy from PostgreSQL full-text search. Replies quote the
retrieved policy and return structured citations. The third tool creates tickets, but it is behind
a human approval boundary: the first call writes a short-lived proposal to Redis, and a separate
approval call atomically consumes that proposal before inserting the ticket in PostgreSQL.

I chose Redis for approval state because the records are temporary and need TTL plus atomic
single-use semantics. PostgreSQL holds durable business records and policy documents. The agent has
only three registered tools, so its permissions are easy to audit.

## Good details to discuss

- The GIN index makes policy lookup fast without introducing a vector database for a small corpus.
- Structured citations make correctness measurable; checking only fluent text would be subjective.
- `GETDEL` makes approval tokens single-use, which prevents duplicate tickets on retries.
- The 100-case benchmark covers four intent groups and includes 20 approval-required escalations.
- Tool success and latency are captured per call, so a bad answer can be separated from an
  infrastructure failure.
- The default composer is extractive and deterministic. A model-backed composer could be added
  later without widening tool permissions or changing the approval boundary.

## Tradeoffs and next steps

- Full-text search is appropriate for a small, vocabulary-controlled policy corpus. For thousands
  of less structured documents, add embeddings and hybrid ranking, then evaluate whether recall
  improves enough to justify the added service.
- Redis can lose a proposal without losing a durable customer record. In a regulated workflow,
  proposals and approval decisions should also be written to an audit table.
- The API currently trusts the caller's account ID. Production needs authentication, tenant checks,
  rate limiting, and separate roles for proposing and approving actions.
- A production benchmark should include adversarial prompts, stale policies, database faults, and
  concurrent approval retries in addition to the happy-path dataset.

## Demo sequence

1. Call `GET /v1/tools` and show that only three tools are exposed.
2. Ask a refund question and point out `[P1]` plus the structured citation.
3. Ask to create a ticket and show `awaiting_approval` while the tickets table is unchanged.
4. Approve the returned action ID, fetch the ticket, and retry approval to demonstrate single use.
5. Run the benchmark and explain task completion, citation correctness, failures, p95 latency, and
   cost per request.
