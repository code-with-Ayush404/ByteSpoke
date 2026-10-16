import argparse
import json
from pathlib import Path
from scd2 import DB_PATH, get_history, initialize, load_file, reset_database
from reporting import generate_report


def main():
    parser = argparse.ArgumentParser(description="SCD Type 2 customer dimension pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create the database and tables")
    load_parser = sub.add_parser("load", help="Load a customer change CSV")
    load_parser.add_argument("csv_path", help="Path to CSV file")
    report_parser = sub.add_parser("report", help="Generate JSON and Markdown reports")
    report_parser.add_argument("--output-dir", default=None)
    show_parser = sub.add_parser("show", help="Show customer version history")
    show_parser.add_argument("--customer-id", default=None)
    sub.add_parser("reset", help="Delete and recreate the local database")
    args = parser.parse_args()

    if args.command == "init":
        initialize()
        print(f"Database initialized: {DB_PATH}")
    elif args.command == "load":
        print(json.dumps(load_file(args.csv_path), indent=2))
    elif args.command == "report":
        print(json.dumps(generate_report(output_dir=args.output_dir), indent=2))
    elif args.command == "show":
        print(json.dumps(get_history(args.customer_id), indent=2))
    elif args.command == "reset":
        reset_database()
        print("Database reset.")

if __name__ == "__main__":
    main()
