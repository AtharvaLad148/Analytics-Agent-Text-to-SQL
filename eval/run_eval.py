"""Before/after eval: run every golden question twice, with the context layer
OFF (bare schema only) and ON (schema + semantic layer + few-shot examples),
score both against the reference-SQL result, and report the accuracy lift plus
hallucination rate, latency, and token cost.

Scoring is execution match: the agent's result set is compared to the reference
query's result set (order-independent, floats rounded), so no number is hardcoded.

Writes a per-question CSV and appends a one-line summary to results/history.csv,
so prompt/model changes show up as the number moving over time (Project 7).
"""
import csv
import datetime
import statistics
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.sql_agent import answer, run_sql       # noqa: E402
from agent.schema import unknown_identifiers      # noqa: E402
from agent.config import GOLDEN_PATH              # noqa: E402

GOLDEN = Path(GOLDEN_PATH)
RESULTS_DIR = ROOT / "eval" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def normalize(df):
    rows = []
    for _, r in df.iterrows():
        vals = [round(v, 2) if isinstance(v, float) else v for v in r.values]
        rows.append(tuple(vals))
    return sorted(rows, key=lambda t: tuple(str(x) for x in t))


def results_match(agent_df, ref_df):
    try:
        return normalize(agent_df) == normalize(ref_df)
    except Exception:
        return False


def run_mode(question, include_context, ref_df):
    """Return (match, result_or_None, error)."""
    try:
        res = answer(question, include_context=include_context)
        return results_match(res["data"], ref_df), res, ""
    except Exception as e:
        return False, None, str(e)[:200]


def main():
    cases = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"eval_{ts}.csv"

    rows = []
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["question", "tests", "match_bare", "match_full",
                    "halluc_bare", "halluc_full", "latency_s",
                    "tokens_in", "tokens_out", "cost_inr", "error"])
        for case in cases:
            q = case["question"]
            try:
                ref_df = run_sql(case["reference_sql"])
            except Exception as e:
                print(f"[ref SQL FAILED] {q}: {e}")
                continue
            m_bare, res_bare, err_bare = run_mode(q, False, ref_df)
            m_full, res_full, err_full = run_mode(q, True, ref_df)

            h_bare = bool(unknown_identifiers(res_bare["sql"])) if res_bare else ""
            h_full = bool(unknown_identifiers(res_full["sql"])) if res_full else ""
            latency = res_full["latency_s"] if res_full else ""
            tin = res_full["tokens_in"] if res_full else ""
            tout = res_full["tokens_out"] if res_full else ""
            cost = res_full["cost_inr"] if res_full else ""
            err = err_full or err_bare

            w.writerow([q, case.get("tests", ""), m_bare, m_full,
                        h_bare, h_full, latency, tin, tout, cost, err])
            rows.append({"m_bare": m_bare, "m_full": m_full, "h_full": h_full,
                         "latency": latency, "tin": tin, "tout": tout, "cost": cost})
            mark = {True: "OK", False: "XX"}
            print(f"  bare[{mark[m_bare]}] full[{mark[m_full]}]  {q}")

    n = len(rows)
    bare = sum(1 for r in rows if r["m_bare"])
    full = sum(1 for r in rows if r["m_full"])
    acc_bare = round(100 * bare / n, 1) if n else 0
    acc_full = round(100 * full / n, 1) if n else 0
    h_full = sum(1 for r in rows if r["h_full"] is True)
    lat = [r["latency"] for r in rows if isinstance(r["latency"], (int, float))]
    cost = sum(r["cost"] for r in rows if isinstance(r["cost"], (int, float)))
    tin = sum(r["tin"] for r in rows if isinstance(r["tin"], int))
    tout = sum(r["tout"] for r in rows if isinstance(r["tout"], int))
    avg_lat = round(statistics.mean(lat), 2) if lat else 0

    print("\n" + "=" * 56)
    print(f"Accuracy   bare {bare}/{n} = {acc_bare}%   "
          f"full {full}/{n} = {acc_full}%   lift +{round(acc_full - acc_bare, 1)} pp")
    print(f"Hallucination (full): {h_full}/{n}")
    print(f"Avg latency (full):   {avg_lat} s")
    print(f"Tokens (full total):  in {tin:,}  out {tout:,}")
    print(f"Cost (full total):    Rs {round(cost, 3)}   "
          f"(avg Rs {round(cost / n, 4) if n else 0}/query)")
    print(f"Saved: {out}")

    hist = RESULTS_DIR / "history.csv"
    is_new = not hist.exists()
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp", "n", "acc_bare_pct", "acc_full_pct",
                        "lift_pp", "halluc_full", "avg_latency_s", "cost_inr_total"])
        w.writerow([ts, n, acc_bare, acc_full, round(acc_full - acc_bare, 1),
                    h_full, avg_lat, round(cost, 3)])


if __name__ == "__main__":
    main()
