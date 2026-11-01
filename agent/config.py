import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# Load .env from the project root explicitly, regardless of the current directory.
# override=True so the project's .env wins over ambient env vars (the harness sets
# ANTHROPIC_BASE_URL, which would otherwise shadow the gateway URL below). We grab
# an explicitly-set shell DATASET first so `DATASET=upi python ...` still switches
# datasets without editing .env.
_shell_dataset = os.environ.get("DATASET")
load_dotenv(ROOT / ".env", override=True)

# Which dataset bundle to use. A bundle lives in datasets/<name>/ and holds the
# semantic layer, few-shot examples, and golden set for that dataset; its DuckDB
# is data/<name>.duckdb. Switching datasets is one env var (DATASET=...): the
# agent code never changes, which is the whole schema-driven claim.
DATASET = _shell_dataset or os.getenv("DATASET", "olist")
DATASET_DIR = ROOT / "datasets" / DATASET

_db = os.getenv("DB_PATH") or f"data/{DATASET}.duckdb"
DB_PATH = _db if os.path.isabs(_db) else str(ROOT / _db)

SEMANTIC_LAYER_PATH = os.getenv("SEMANTIC_LAYER_PATH") or str(DATASET_DIR / "semantic_layer.yaml")
EXAMPLES_PATH = os.getenv("EXAMPLES_PATH") or str(DATASET_DIR / "examples.yaml")
GOLDEN_PATH = os.getenv("GOLDEN_PATH") or str(DATASET_DIR / "golden_set.yaml")

MODEL = os.getenv("AGENT_MODEL", "anthropic/claude-sonnet-5.5")
# Optional LLM gateway base URL (e.g. FastRouter). Unset means Anthropic's API.
BASE_URL = os.getenv("ANTHROPIC_BASE_URL") or None
MAX_ROWS = 1000

# Cost metric. USD per 1M tokens; defaults are FastRouter's published price for
# claude-sonnet-5.5. Override via env if the model or gateway changes.
PRICE_IN_PER_MTOK = float(os.getenv("PRICE_IN_PER_MTOK", "2.0"))
PRICE_OUT_PER_MTOK = float(os.getenv("PRICE_OUT_PER_MTOK", "10.0"))
USD_TO_INR = float(os.getenv("USD_TO_INR", "88.0"))
