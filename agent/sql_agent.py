"""The agent: question -> SQL -> validate -> run -> (repair once) -> result."""
import re
import sys
import time

from .config import (
    MODEL,
    MAX_ROWS,
    PRICE_IN_PER_MTOK,
    PRICE_OUT_PER_MTOK,
    USD_TO_INR,
)
from .llm import new_client, message_text
from .prompt import build_system_prompt
from .schema import get_connection
from .validate import validate_sql

MAX_TOKENS = 1000


def _client():
    # Anthropic client, optionally routed through a gateway (see agent/llm.py).
    return new_client()


def _ask(system, user, client):
    return client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )


def _extract_sql(text):
    m = re.search(r"```sql\s*(.*?)```", text, re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    return sql.rstrip(";").strip()


def _add_limit(sql):
    if re.search(r"\blimit\b", sql, re.I):
        return sql
    return f"{sql}\nLIMIT {MAX_ROWS}"


def generate_sql(question, client=None, include_context=True):
    """Return (sql, usage) where usage is the Anthropic token-usage object."""
    client = client or _client()
    resp = _ask(build_system_prompt(include_context=include_context),
                f"Question: {question}", client)
    sql = _add_limit(validate_sql(_extract_sql(message_text(resp))))
    return sql, resp.usage


def run_sql(sql):
    con = get_connection(read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def answer(question, client=None, repair=True, include_context=True):
    client = client or _client()
    t0 = time.time()
    tokens_in = tokens_out = 0

    sql, usage = generate_sql(question, client, include_context=include_context)
    tokens_in += usage.input_tokens
    tokens_out += usage.output_tokens
    try:
        df = run_sql(sql)
    except Exception as e:
        if not repair:
            raise
        user = (
            f"Question: {question}\n\nThis SQL failed:\n{sql}\n\n"
            f"Error: {e}\n\nReturn a corrected SQL query."
        )
        resp = _ask(build_system_prompt(include_context=include_context), user, client)
        tokens_in += resp.usage.input_tokens
        tokens_out += resp.usage.output_tokens
        sql = _add_limit(validate_sql(_extract_sql(message_text(resp))))
        df = run_sql(sql)

    cost_usd = (tokens_in / 1_000_000) * PRICE_IN_PER_MTOK + \
               (tokens_out / 1_000_000) * PRICE_OUT_PER_MTOK
    return {
        "question": question,
        "sql": sql,
        "data": df,
        "latency_s": round(time.time() - t0, 2),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 6),
        "cost_inr": round(cost_usd * USD_TO_INR, 4),
    }


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is total revenue by product category?"
    res = answer(q)
    print("\nSQL:\n" + res["sql"])
    print("\nResult:\n" + res["data"].to_string(index=False))
    print(f"\nLatency: {res['latency_s']}s  |  tokens in/out: "
          f"{res['tokens_in']}/{res['tokens_out']}  |  cost: Rs {res['cost_inr']}")
