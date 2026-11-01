"""Tests for the read-only SQL guardrail (agent/validate.py).

These are pure-function tests: no database, no API key, no network. They pin the
safety contract so a future prompt or model change cannot silently let a write
through.
"""
from pathlib import Path

import pytest
import yaml

from agent.validate import validate_sql
from agent.config import GOLDEN_PATH

ROOT = Path(__file__).resolve().parent.parent


# --- Queries that MUST be allowed -------------------------------------------

ALLOWED = [
    "SELECT 1",
    "select * from customers",
    "WITH x AS (SELECT 1 AS a) SELECT a FROM x",
    "SELECT 1 AS a UNION SELECT 2",
    # a realistic multi-join analytics query (shape of the golden set)
    """
    SELECT p.category, SUM(oi.quantity * oi.item_price) AS revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.status = 'completed'
    GROUP BY p.category
    """,
    # a column literally named "replace" must not trip a keyword blocklist
    "SELECT replace(city, 'a', 'b') AS city2 FROM customers",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allows_read_only_queries(sql):
    assert validate_sql(sql) == sql


def test_every_golden_reference_sql_validates():
    """No real reference query in the golden set should be wrongly rejected."""
    cases = yaml.safe_load(Path(GOLDEN_PATH).read_text(encoding="utf-8"))
    for case in cases:
        sql = case["reference_sql"]
        assert validate_sql(sql) == sql, f"wrongly rejected: {sql!r}"


# --- Queries that MUST be rejected ------------------------------------------

FORBIDDEN = [
    "INSERT INTO customers VALUES (1)",
    "UPDATE customers SET city = 'X'",
    "DELETE FROM customers",
    "DROP TABLE customers",
    "CREATE TABLE t AS SELECT 1",
    "ALTER TABLE customers ADD COLUMN c INT",
    "ATTACH DATABASE 'evil.db'",
    "COPY customers TO 'out.csv'",
    "PRAGMA table_info(customers)",
    # SELECT ... INTO writes a new table: the classic prefix-check bypass
    "SELECT * INTO backup FROM customers",
    # stacked statements: the SELECT prefix looks fine, the second is a write
    "SELECT 1; DROP TABLE customers",
    # not a query at all
    "",
    "not sql at all ;;;",
]


@pytest.mark.parametrize("sql", FORBIDDEN)
def test_rejects_writes_and_non_selects(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)
