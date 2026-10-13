# Design notes

## Request path

1. `account_lookup` confirms the account and returns only the fields needed for a reply.
2. `policy_search` expands common customer language, runs PostgreSQL full-text search, and
   returns ranked policy passages.
3. The response composer uses the highest-ranked passage and adds a citation marker. Citation
   metadata is returned separately so clients do not need to parse the message.
4. If the customer asks for a human or retrieval cannot support an answer, `create_ticket`
   stores a proposed action in Redis. No ticket row is written at this point.
5. The approval endpoint atomically consumes the proposal with Redis `GETDEL` and creates the
   ticket. A retry cannot execute the same approval twice.

```text
request
  |
  +--> account_lookup ---------> PostgreSQL accounts
  |
  +--> policy_search ----------> PostgreSQL policy full-text index
  |                                  |
  |                                  +--> cited response
  |
  +--> create_ticket proposal -> Redis (15 minute TTL)
                                     |
human approval ----------------------+--> PostgreSQL tickets
```

## Why the approval is separate

Read operations can be retried safely. Ticket creation cannot: an automatic retry could create
duplicates, and a misclassified request could modify a customer record without consent. The
proposal is therefore short-lived, inspectable, and single-use. Redis supplies expiration and an
atomic consume operation; PostgreSQL remains the system of record.

## Retrieval

Policies are indexed with PostgreSQL `tsvector` and a GIN expression index. Query expansion maps
phrases such as "charged" to billing, payment, and refund terms before ranking results with
`ts_rank_cd`. A small deterministic fallback ranker keeps the repository testable with SQLite.
The composer is intentionally extractive: it uses policy sentences rather than inventing details,
which makes citation checks stable and keeps the local demo free of model credentials.

## Failure behavior

- Unknown account: stop before policy retrieval or ticket proposal.
- No relevant policy: avoid an unsupported answer and propose escalation.
- Redis unavailable: reads can still be diagnosed, but approval proposals fail visibly as a tool
  failure instead of bypassing the gate.
- Repeated or expired approval: return `404`; no second ticket is created.
- Database failure: the API returns an error and the transaction does not commit.

## Benchmark contract

`eval/cases.jsonl` contains exactly 100 labeled requests across billing, access, subscription, and
privacy. Twenty of them explicitly require escalation. A request counts as complete when its state
and expected citation are both correct. Citation correctness checks whether the expected policy is
present, while citation precision penalizes extra retrieved policies. Client latency is measured
around the HTTP request; tool failures and the server's estimated request cost come from the API
response.

The default response composer has no per-request model charge, so estimated model cost is `$0`.
PostgreSQL, Redis, and host costs are intentionally not folded into that field.
