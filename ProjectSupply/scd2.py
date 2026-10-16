"""SCD Type 2 ingestion logic using only Python's standard library."""
import csv
import hashlib
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "customer_history.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
REQUIRED_COLUMNS = ["customer_id", "customer_name", "city", "segment", "effective_date"]
TRACKED_FIELDS = ["customer_name", "city", "segment"]


class DataQualityError(ValueError):
    """Raised when an input file violates data quality rules."""


@contextmanager
def connect(db_path=DB_PATH):
    """Yield a SQLite connection and always close it, including on Windows."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(db_path=DB_PATH):
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def _parse_csv(path):
    raw = Path(path).read_text(encoding="utf-8-sig")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
    batch_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    reader = csv.DictReader(io.StringIO(normalized))
    if reader.fieldnames is None:
        raise DataQualityError("CSV is empty or has no header.")
    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise DataQualityError(f"Missing required column(s): {', '.join(missing)}")

    rows = []
    seen = set()
    for line_no, raw_row in enumerate(reader, start=2):
        row = {key: (raw_row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
        if any(not row[key] for key in REQUIRED_COLUMNS):
            raise DataQualityError(f"Line {line_no}: all required fields must be non-empty.")
        try:
            date.fromisoformat(row["effective_date"])
        except ValueError:
            raise DataQualityError(f"Line {line_no}: effective_date must be YYYY-MM-DD.")
        if row["customer_id"] in seen:
            raise DataQualityError(
                f"Line {line_no}: duplicate customer_id {row['customer_id']} in one file."
            )
        seen.add(row["customer_id"])
        rows.append(row)
    if not rows:
        raise DataQualityError("CSV has a header but no data rows.")
    return normalized, batch_id, rows


def _attributes(row):
    return {field: row[field] for field in TRACKED_FIELDS}


def load_file(path, db_path=DB_PATH):
    """Load a CSV atomically. Returns a summary dictionary."""
    path = Path(path)
    _, batch_id, rows = _parse_csv(path)
    initialize(db_path)

    with connect(db_path) as conn:
        existing_batch = conn.execute(
            "SELECT batch_id FROM processed_batches WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        if existing_batch:
            return {
                "status": "skipped_duplicate_batch",
                "batch_id": batch_id,
                "rows": len(rows),
                "inserted_versions": 0,
                "skipped_rows": len(rows),
                "message": "This exact file content was already processed; no changes made."
            }

        inserted = 0
        skipped = 0
        events = []

        # Validate every row before applying any changes, so an invalid file is atomic.
        for row in rows:
            current = conn.execute(
                "SELECT * FROM dim_customer WHERE customer_id = ? AND is_current = 1",
                (row["customer_id"],)
            ).fetchone()
            if current and row["effective_date"] < current["effective_from"]:
                raise DataQualityError(
                    f"Customer {row['customer_id']}: effective_date {row['effective_date']} "
                    f"is earlier than current version start {current['effective_from']}."
                )

        # Apply all changes within this transaction.
        for row in rows:
            current = conn.execute(
                "SELECT * FROM dim_customer WHERE customer_id = ? AND is_current = 1",
                (row["customer_id"],)
            ).fetchone()
            after = _attributes(row)
            if current is None:
                conn.execute(
                    """INSERT INTO dim_customer
                    (customer_id, customer_name, city, segment, effective_from, effective_to, is_current)
                    VALUES (?, ?, ?, ?, ?, NULL, 1)""",
                    (row["customer_id"], row["customer_name"], row["city"], row["segment"],
                     row["effective_date"])
                )
                events.append({
                    "batch_id": batch_id, "customer_id": row["customer_id"],
                    "effective_date": row["effective_date"], "event_type": "INSERT",
                    "changed_fields": TRACKED_FIELDS, "before": None, "after": after
                })
                inserted += 1
            else:
                before = {field: current[field] for field in TRACKED_FIELDS}
                changed_fields = [field for field in TRACKED_FIELDS if before[field] != after[field]]
                if not changed_fields:
                    skipped += 1
                    continue
                if row["effective_date"] == current["effective_from"]:
                    raise DataQualityError(
                        f"Customer {row['customer_id']}: changed attributes share the same "
                        "effective_date as the current version; use a later date."
                    )
                conn.execute(
                    """UPDATE dim_customer
                    SET effective_to = ?, is_current = 0
                    WHERE customer_sk = ?""",
                    (row["effective_date"], current["customer_sk"])
                )
                conn.execute(
                    """INSERT INTO dim_customer
                    (customer_id, customer_name, city, segment, effective_from, effective_to, is_current)
                    VALUES (?, ?, ?, ?, ?, NULL, 1)""",
                    (row["customer_id"], row["customer_name"], row["city"], row["segment"],
                     row["effective_date"])
                )
                events.append({
                    "batch_id": batch_id, "customer_id": row["customer_id"],
                    "effective_date": row["effective_date"], "event_type": "UPDATE",
                    "changed_fields": changed_fields, "before": before, "after": after
                })
                inserted += 1

        conn.execute(
            """INSERT INTO processed_batches
            (batch_id, source_name, row_count, inserted_versions, skipped_rows)
            VALUES (?, ?, ?, ?, ?)""",
            (batch_id, path.name, len(rows), inserted, skipped)
        )
        for event in events:
            conn.execute(
                """INSERT INTO change_events
                (batch_id, customer_id, effective_date, event_type,
                 changed_fields_json, before_json, after_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event["batch_id"], event["customer_id"], event["effective_date"],
                 event["event_type"], json.dumps(event["changed_fields"], sort_keys=True),
                 json.dumps(event["before"], sort_keys=True) if event["before"] is not None else None,
                 json.dumps(event["after"], sort_keys=True))
            )

    return {
        "status": "processed", "batch_id": batch_id, "rows": len(rows),
        "inserted_versions": inserted, "skipped_rows": skipped,
        "message": "Batch processed successfully."
    }


def get_history(customer_id=None, db_path=DB_PATH):
    initialize(db_path)
    with connect(db_path) as conn:
        if customer_id:
            rows = conn.execute(
                "SELECT * FROM dim_customer WHERE customer_id = ? ORDER BY effective_from, customer_sk",
                (customer_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM dim_customer ORDER BY customer_id, effective_from, customer_sk"
            ).fetchall()
        return [dict(row) for row in rows]


def get_events(db_path=DB_PATH):
    initialize(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM change_events ORDER BY event_id"
        ).fetchall()
        return [dict(row) for row in rows]


def reset_database(db_path=DB_PATH):
    path = Path(db_path)
    if path.exists():
        path.unlink()
    initialize(db_path)
