# 5–8 Minute Demo Script

## 0:00–0:45 — Introduce the problem
“Customer city and segment can change over time. If we overwrite the row, we lose history. This project uses SCD Type 2 to keep old and current versions.”

## 0:45–1:30 — Show the input files
Open `data/customer_changes_1.csv` and `data/customer_changes_2.csv`. Explain that the data is synthetic and each row is a customer snapshot as of `effective_date`.

## 1:30–2:15 — Run the first batch
```bash
python main.py reset
python main.py load data/customer_changes_1.csv
python main.py show --customer-id C1001
```
Explain that the first record creates the initial current version.

## 2:15–3:15 — Run changed snapshots
```bash
python main.py load data/customer_changes_2.csv
python main.py show --customer-id C1001
```
Point out that the old Lucknow/Standard version is closed at `2026-03-01` and a new Delhi/Premium version is current. C1002 is unchanged, so no new version is created for that customer.

## 3:15–4:00 — Prove idempotency
```bash
python main.py load data/customer_changes_2.csv
```
The result should say `skipped_duplicate_batch`. Explain that the content hash prevents duplicate processing.

## 4:00–5:00 — Show the AI-readable report
```bash
python main.py report
```
Open `reports/change_report.json`. Each event includes customer ID, effective date, changed fields, before and after values, event type, and batch ID.

## 5:00–6:30 — Run tests
```bash
python -m unittest discover -s tests -v
```
Mention coverage of history preservation, unchanged rows, reruns, invalid dates/order, duplicate customer keys, and report generation.

## 6:30–7:00 — Close
“SQLite and local CSVs make this reproducible from a clean setup. A production version could use PostgreSQL and a scheduler, with a defined policy for late-arriving changes.”
