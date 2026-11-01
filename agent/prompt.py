"""Build the context the LLM needs: schema + semantic layer + samples + rules."""
from pathlib import Path

import yaml

from .config import SEMANTIC_LAYER_PATH, EXAMPLES_PATH
from .schema import get_schema_text, get_sample_rows


def load_semantic_layer():
    p = Path(SEMANTIC_LAYER_PATH)
    if not p.exists():
        return "(none provided)"
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    lines = []

    dataset = data.get("dataset")
    if dataset:
        lines.append(f"Dataset: {dataset}")
        lines.append("")

    for t, info in (data.get("tables", {}) or {}).items():
        info = info or {}
        head = f"Table {t}"
        if info.get("grain"):
            head += f" (grain: {info['grain']})"
        desc = info.get("description", "")
        lines.append(f"{head}: {desc}".rstrip())
        for col, cdesc in (info.get("columns", {}) or {}).items():
            lines.append(f"  - {col}: {cdesc}")
        for j in (info.get("joins", []) or []):
            lines.append(f"  join: {j}")
        if info.get("notes"):
            lines.append(f"  note: {info['notes']}")
        lines.append("")

    def _bullets(title, items):
        if items:
            lines.append(title)
            for it in items:
                lines.append(f"  - {it}")
            lines.append("")

    _bullets("Business rules (follow exactly):", data.get("business_rules", []) or [])
    _bullets("DuckDB dialect notes:", data.get("dialect_notes", []) or [])

    metrics = data.get("metrics", {}) or {}
    if metrics:
        lines.append("Metric definitions (use these exactly):")
        for m, d in metrics.items():
            lines.append(f"  - {m}: {d}")

    text = "\n".join(lines).strip()
    return text if text else "(none provided)"


SYSTEM_TEMPLATE = """You are a careful analytics engineer who writes DuckDB SQL.

Rules:
- Return ONLY one SQL query inside a ```sql code block. No explanation.
- Use SELECT statements only (read-only). Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, or PRAGMA.
- Use only the tables and columns in the schema below. Never invent a column.
- Follow the metric definitions in the semantic layer exactly.
- DuckDB dialect. Prefer clear, correct SQL.

Database schema:
{schema}

Semantic layer (business meaning and metric definitions):
{semantic}

Sample rows:
{samples}
{examples}"""


def load_examples():
    """Verified question -> SQL pairs that teach the join chains and idioms."""
    p = Path(EXAMPLES_PATH)
    if not p.exists():
        return ""
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    blocks = []
    for ex in (data.get("examples", []) or []):
        q = (ex.get("question") or "").strip()
        sql = (ex.get("sql") or "").strip()
        if q and sql:
            blocks.append(f"Q: {q}\n```sql\n{sql}\n```")
    return "\n\n".join(blocks)


def build_system_prompt(include_context=True):
    """Build the system prompt.

    include_context=True is the real agent: schema + semantic layer + few-shot
    examples. include_context=False is the bare baseline (schema + sample rows
    only), used by the eval to measure what the semantic layer and examples add.
    """
    if include_context:
        semantic = load_semantic_layer()
        examples = load_examples()
    else:
        semantic = "(none provided)"
        examples = ""
    examples_block = (
        f"\nWorked examples (correct SQL for this database, follow these patterns):\n{examples}\n"
        if examples
        else ""
    )
    return SYSTEM_TEMPLATE.format(
        schema=get_schema_text(),
        semantic=semantic,
        samples=get_sample_rows(),
        examples=examples_block,
    )
