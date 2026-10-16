# Design / Decision Note — DAI-037

## Goal
Build a repeatable customer-dimension pipeline that preserves historical attribute values (SCD Type 2), avoids duplicate versions on reruns, and publishes a machine-readable change report.

## Architecture
1. **CSV input** — synthetic snapshots with customer business key and effective date.
2. **Validation** — required columns, non-empty fields, ISO dates, one row per customer per batch, and no out-of-order updates.
3. **Batch identity** — SHA-256 of normalized file content provides deterministic idempotency.
4. **Storage** — SQLite dimension table plus processed-batch and change-event tables.
5. **Reporting** — JSON event records and a Markdown summary.

## SCD Type 2 rules
- First observation inserts a current version.
- If tracked fields (`customer_name`, `city`, `segment`) do not change, the row is skipped.
- If one or more tracked fields change, the old version is closed at the incoming effective date and a new current version is inserted.
- `effective_to` is exclusive; `NULL` means the current version.
- A partial unique index ensures at most one current row per customer.

## Key decisions
- **SQLite** keeps the demo self-contained and runnable without a server.
- **Standard-library Python** avoids dependency installation and network requirements.
- **Content hash** makes exact reruns safe even if the source filename changes.
- **Transactions** prevent partial updates when a batch fails.
- **Reject late-arriving/out-of-order changes** rather than guessing how to rewrite history. A production system should define a business-approved correction policy.
- **No external LLM call** is made. The JSON report is an AI-ready interface with structured before/after values; a future model can be added behind a separate adapter without coupling it to ingestion.

## Validation
Automated tests cover first insert, changed attributes/history preservation, idempotent rerun, unchanged values, out-of-order dates, duplicate keys, and report generation.
