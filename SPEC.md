# Project 1: Analytics Agent (Text-to-SQL + Insight Narrator)

**Series:** BUILD with AI | **Author:** Atharva Lad | **Type:** GenAI + Product Analytics

## 1. One-liner
A schema-driven agent that takes a plain-English business question, writes and runs SQL against a database, and returns the answer with a chart and a short "so what" recommendation. Works on any dataset, measured by an eval harness.

## 2. Why (what it proves to a hiring manager)
- GenAI prototyping and agentic / text-to-SQL (the most-named 2026 JD skill: "Analytics Agents", "AI-augmented decision tools").
- Product-analyst depth: metric definitions, a semantic layer, and insight-to-decision framing, not just a dev toy.
- Measurement maturity: an eval harness that reports accuracy, hallucination rate, latency, and cost.

## 3. Scope
**In (v1):**
- Natural-language question in, SQL + result table + one chart + a plain-language insight out.
- Schema introspected at runtime (no hardcoded columns). Portable across datasets.
- A semantic layer (data dictionary + metric definitions) to improve accuracy.
- Read-only guardrails and basic error-repair (retry on failed SQL).
- An eval harness with a golden question set and scored metrics.
- A simple Streamlit UI.

**Out (v1, note as "next steps"):**
- Multi-turn conversation / memory.
- Charts beyond a sensible default per result shape.
- Auth, multi-user, deployment to a server (local demo is fine).

## 4. Datasets (schema-driven, so it generalizes)
- **Primary (relational, for real joins):** an Indian e-commerce sales dataset with order, order-detail, and target tables (verify columns on download); Olist (Brazilian, 9 tables) is the richer fallback.
- **Secondary demo (fintech):** Indian UPI transactions (single large fact table, realistic for payments).
- Demoing the same agent on both datasets proves it is not hardcoded. Confirm real columns before building.

## 5. Architecture (flow)
1. **User question** (Streamlit input).
2. **Schema introspection:** read tables, columns, types from DuckDB `information_schema` at runtime.
3. **Context build:** schema text + data dictionary + metric definitions + 3 to 5 sample rows per table + a few example question-to-SQL pairs.
4. **LLM writes SQL** (Claude or OpenAI API), told the dialect (DuckDB) and the read-only rule.
5. **Validate:** confirm it is a single SELECT, add a row LIMIT, reject writes/DDL.
6. **Execute** against DuckDB; on error, feed the error back to the LLM once to repair.
7. **Narrate:** LLM turns the result into a 2 to 3 line insight plus a recommendation.
8. **Chart:** pick a default chart from the result shape (time series to line, category to bar).
9. **Show** SQL + table + chart + insight in the UI.

## 6. Semantic layer (the product-analyst value-add)
A small config file (YAML/JSON) holding:
- Plain-English description of each table and column.
- Enum/code meanings (e.g., status codes, category codes).
- Metric definitions (how "conversion", "AOV", "fraud rate" are computed in SQL terms).
This is injected into the prompt and is what moves accuracy from "plausible" to "correct".

## 7. Guardrails
- Read-only connection; reject anything that is not a SELECT.
- Enforce a row LIMIT on every query.
- Timeout on query execution.
- Never expose raw API keys; load from environment.

## 8. Eval harness
- **Golden set:** 30 to 50 questions with known-correct answers (and ideally the reference SQL).
- **Metrics per run:** answer accuracy (exact match on the numeric/category result), SQL execution success rate, hallucination rate (references a column/value that does not exist), latency (s/query), cost (tokens and rupees/query).
- **Narrative quality:** LLM-as-judge against a short rubric (correct, specific, actionable).
- **Versioning:** store each run's scores in a CSV so prompt/model changes show as up or down. This is also Project 7.

## 9. Tech stack
- Python 3.x, DuckDB (local analytical DB), pandas.
- LLM: Anthropic (Claude) or OpenAI API.
- UI: Streamlit.
- Charts: Plotly or matplotlib.
- Config: YAML for the semantic layer. Env vars for keys.

## 10. Repo structure
```
01_analytics_agent/
  README.md
  requirements.txt
  .env.example            (API key placeholder)
  data/                   (downloaded CSVs, gitignored)
  load_data.py            (CSVs -> DuckDB)
  semantic_layer.yaml     (data dictionary + metric defs)
  agent/
    schema.py             (introspect schema)
    prompt.py             (build the context)
    sql_agent.py          (LLM call + validate + execute + repair)
    narrate.py            (result -> insight)
    charts.py             (result -> chart)
  app.py                  (Streamlit UI)
  eval/
    golden_set.yaml       (questions + expected answers)
    run_eval.py           (score + log metrics)
    results/              (per-run CSVs)
```

## 11. Build plan (about 1 to 2 weeks, part-time)
- **Day 1 to 2:** pick + download dataset, verify columns, write `load_data.py` (CSVs to DuckDB), write `semantic_layer.yaml`.
- **Day 3 to 4:** schema introspection + prompt builder + first working text-to-SQL call (no UI yet, run from a script).
- **Day 5:** guardrails + error-repair loop + narration.
- **Day 6:** Streamlit UI (question box, SQL, table, chart, insight).
- **Day 7 to 8:** build the golden set (30 to 50 Qs) + `run_eval.py` + first scored run.
- **Day 9:** improve the semantic layer and prompt using eval results; re-run to show the lift.
- **Day 10:** second dataset (UPI) to prove generalization; write README + LinkedIn post.

## 12. Deliverables
- **GitHub repo** with the structure above and a strong README.
- **README sections:** Problem -> Data -> Approach (incl. the AI and the schema-driven design) -> Key results (eval metrics) -> Product framing (example question -> insight -> decision) -> What I'd do next.
- **A demo GIF/screenshot** of the UI answering a question.
- **LinkedIn write-up** (see outline below).

## 13. LinkedIn write-up outline
1. Hook: the problem (analysts spend hours writing repetitive SQL for stakeholder questions).
2. What I built (one line + a screenshot/GIF).
3. How it works (schema-driven, so it runs on any dataset; semantic layer for accuracy).
4. The part most people skip: I measured it (accuracy %, hallucination %, latency, cost).
5. A real example: question -> insight -> the product decision it enables.
6. What I learned about building with LLMs + what is next in the series.
7. Link to the repo. Ask a question to invite comments.

## 14. Success criteria (v1 "done")
- Answers at least 80% of the golden-set questions correctly, end to end.
- Runs on a second dataset with no code changes (schema-driven proven).
- Eval metrics reported in the README with a before/after showing the semantic layer improved accuracy.
- A clean README and a published LinkedIn post.

## 15. Stretch (later)
- Multi-turn follow-ups ("now break that by state").
- Auto-insight mode (it proposes the 3 most interesting findings unprompted) -> leads into Project 10 (agentic daily insights).
- Caching + cost optimization.
