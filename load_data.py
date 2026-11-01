"""Load a folder of CSVs into a DuckDB database, one table per file.

Dataset-agnostic on purpose: the agent code never changes when you swap datasets.
Point this at a folder of CSVs and it builds <db>.duckdb with one table per file,
the table named from the file (olist_orders_dataset.csv -> orders).

Usage:
  python load_data.py data/olist data/olist.duckdb
"""
import re
import sys
from pathlib import Path

import duckdb


def table_name(csv_path):
    """Turn a CSV filename into a clean SQL table name.

    Strips a leading 'olist_' and a trailing '_dataset' (the Olist convention)
    and squashes anything non-alphanumeric to single underscores.
    """
    name = csv_path.stem.lower()
    name = re.sub(r"^olist_", "", name)
    name = re.sub(r"_dataset$", "", name)
    name = re.sub(r"[^0-9a-z]+", "_", name).strip("_")
    return name


def load(csv_dir, db_path):
    csv_dir = Path(csv_dir)
    csvs = sorted(csv_dir.glob("*.csv"))
    if not csvs:
        raise SystemExit(f"No CSV files found in {csv_dir}")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    try:
        for csv in csvs:
            name = table_name(csv)
            # Local, globbed path (not user input). Forward-slash it and escape
            # single quotes so the string literal is safe on every platform.
            literal = str(csv).replace("\\", "/").replace("'", "''")
            con.execute(
                f"CREATE TABLE {name} AS "
                f"SELECT * FROM read_csv_auto('{literal}', header=true, sample_size=-1)"
            )
            rows = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  {name:<28} {rows:>9,} rows  <- {csv.name}")
    finally:
        con.close()
    print(f"Created {db_path} with {len(csvs)} tables")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/olist"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/olist.duckdb"
    load(src, out)
