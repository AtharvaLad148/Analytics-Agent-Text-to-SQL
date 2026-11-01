"""Read-only SQL guardrail, enforced in code rather than by the prompt.

The prompt asks the model for a single read-only SELECT, but a prompt is not a
boundary: a model (or a prompt injection) can still emit a write, and a plain
"starts with SELECT" check misses `SELECT ... INTO`, stacked statements, and
`COPY`/`ATTACH`/`PRAGMA`. This module parses the SQL into an AST (sqlglot, DuckDB
dialect) and rejects anything that is not exactly one read-only query. Paired
with a read-only DuckDB connection and an enforced LIMIT, this is the real
guardrail.
"""
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# The only statement roots allowed: a SELECT, or a set operation over SELECTs.
_ALLOWED_ROOT_NAMES = ["Select", "Union", "Intersect", "Except"]
ALLOWED_ROOTS = tuple(
    getattr(exp, name) for name in _ALLOWED_ROOT_NAMES if hasattr(exp, name)
)

# Any of these nodes anywhere in the tree means the query writes data or runs a
# command, even when the statement begins with SELECT (e.g. SELECT ... INTO).
# Names are looked up defensively so a sqlglot version lacking one still loads.
_FORBIDDEN_NODE_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Into",
    "Create", "Drop", "Alter", "TruncateTable",
    "Attach", "Detach", "Copy", "Pragma", "Command", "Set", "Grant",
]
FORBIDDEN_NODES = tuple(
    getattr(exp, name) for name in _FORBIDDEN_NODE_NAMES if hasattr(exp, name)
)


def parse_duckdb(sql):
    """Parse SQL as DuckDB and return the single statement's AST.

    Raises ValueError if the text does not parse or is not exactly one
    statement. The hallucination check reuses this to read table/column names.
    """
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except ParseError as e:
        raise ValueError(f"Could not parse SQL: {e}")
    statements = [s for s in statements if s is not None]
    if not statements:
        raise ValueError("No SQL statement found.")
    if len(statements) > 1:
        raise ValueError("Only a single statement is allowed.")
    return statements[0]


def validate_sql(sql):
    """Return sql unchanged if it is one read-only query, else raise ValueError."""
    root = parse_duckdb(sql)
    if not isinstance(root, ALLOWED_ROOTS):
        raise ValueError(
            f"Only SELECT queries are allowed (got {type(root).__name__.upper()})."
        )
    bad = {type(n).__name__.upper() for n in root.find_all(*FORBIDDEN_NODES)}
    if bad:
        raise ValueError(
            "Query contains a forbidden operation: " + ", ".join(sorted(bad)) + "."
        )
    return sql
