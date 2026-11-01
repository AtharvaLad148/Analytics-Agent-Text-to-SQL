"""Schema introspection. Nothing hardcoded: the agent reads the live schema."""
import duckdb
from sqlglot import exp

from .config import DB_PATH
from .validate import parse_duckdb


def get_connection(read_only=True):
    return duckdb.connect(DB_PATH, read_only=read_only)


def list_tables():
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def get_schema_text():
    """Return CREATE TABLE-style text for every table in the database."""
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
    finally:
        con.close()
    tables = {}
    for t, c, d in rows:
        tables.setdefault(t, []).append(f"{c} {d}")
    blocks = []
    for t, cols in tables.items():
        cols_str = ",\n  ".join(cols)
        blocks.append(f"CREATE TABLE {t} (\n  {cols_str}\n);")
    return "\n\n".join(blocks)


def get_sample_rows(limit=3):
    con = get_connection()
    out = []
    try:
        for t in list_tables():
            try:
                df = con.execute(f"SELECT * FROM {t} LIMIT {limit}").df()
                out.append(f"-- {t} (sample):\n{df.to_markdown(index=False)}")
            except Exception:
                continue
    finally:
        con.close()
    return "\n\n".join(out)


def _schema_identifiers():
    """Return (table names, all column names) in the live DB, lowercased."""
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'main'"
        ).fetchall()
    finally:
        con.close()
    return {t.lower() for t, _ in rows}, {c.lower() for _, c in rows}


def unknown_identifiers(sql):
    """Tables/columns the SQL references that are not in the live schema.

    A hallucination signal (SPEC section 8). Query-local names (CTEs and output
    aliases) are allowed, so a CTE column does not count as invented.
    """
    try:
        root = parse_duckdb(sql)
    except Exception:
        return []
    tables, columns = _schema_identifiers()
    cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE) if c.alias_or_name}
    local = set(cte_names)
    for a in root.find_all(exp.Alias):
        if a.alias_or_name:
            local.add(a.alias_or_name.lower())

    unknown = set()
    for col in root.find_all(exp.Column):
        n = (col.name or "").lower()
        if n and n not in columns and n not in local:
            unknown.add(col.name)
    for tbl in root.find_all(exp.Table):
        n = (tbl.name or "").lower()
        if n and n not in tables and n not in cte_names:
            unknown.add(tbl.name)
    return sorted(unknown)
