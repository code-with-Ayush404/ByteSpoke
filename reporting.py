"""Generate deterministic, AI-readable change reports. No external AI calls."""
import json
from pathlib import Path
from scd2 import DB_PATH, connect, initialize


def generate_report(db_path=DB_PATH, output_dir=None):
    initialize(db_path)
    output_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT batch_id, customer_id, effective_date, event_type,
                      changed_fields_json, before_json, after_json, created_at
               FROM change_events ORDER BY event_id"""
        ).fetchall()
        stats = conn.execute(
            """SELECT COUNT(*) AS total_versions,
                      COUNT(DISTINCT customer_id) AS customers,
                      SUM(CASE WHEN is_current = 1 THEN 1 ELSE 0 END) AS current_versions
               FROM dim_customer"""
        ).fetchone()

    events = []
    for row in rows:
        events.append({
            "batch_id": row["batch_id"],
            "customer_id": row["customer_id"],
            "effective_date": row["effective_date"],
            "event_type": row["event_type"],
            "changed_fields": json.loads(row["changed_fields_json"]),
            "before": json.loads(row["before_json"]) if row["before_json"] else None,
            "after": json.loads(row["after_json"]),
            "recorded_at": row["created_at"]
        })

    report = {
        "report_type": "customer_dimension_change_report",
        "schema_version": "1.0",
        "summary": {
            "unique_customers": stats["customers"] or 0,
            "total_versions": stats["total_versions"] or 0,
            "current_versions": stats["current_versions"] or 0,
            "change_events": len(events)
        },
        "events": events
    }

    json_path = output_dir / "change_report.json"
    md_path = output_dir / "change_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Customer Dimension Change Report", "",
        f"- Unique customers: **{report['summary']['unique_customers']}**",
        f"- Total versions: **{report['summary']['total_versions']}**",
        f"- Current versions: **{report['summary']['current_versions']}**",
        f"- Change events: **{report['summary']['change_events']}**", "",
        "## Events", ""
    ]
    if not events:
        lines.append("No change events recorded.")
    for event in events:
        changed = ", ".join(event["changed_fields"])
        lines.extend([
            f"### {event['event_type']} — {event['customer_id']} ({event['effective_date']})",
            f"- Changed fields: {changed}",
            f"- Before: `{json.dumps(event['before'], ensure_ascii=False)}`",
            f"- After: `{json.dumps(event['after'], ensure_ascii=False)}`",
            ""
        ])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "summary": report["summary"]}
