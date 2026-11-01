from pathlib import Path

import streamlit as st

from agent.config import DATASET
from agent.sql_agent import answer
from agent.narrate import narrate
from agent.charts import auto_chart

st.set_page_config(page_title="Analytics Agent", layout="wide", page_icon="📊")


def md_safe(text):
    # Insights contain underscores (watches_gifts) and currency ($ / numbers);
    # escape the markdown/LaTeX triggers so st.markdown shows them literally.
    for ch in ("\\", "`", "*", "_", "$"):
        text = text.replace(ch, "\\" + ch)
    return text


# Custom styling (dark theme is set in .streamlit/config.toml; this adds the
# hero, pills, cards, and chips on top).
_css = Path(__file__).parent / "styles.css"
if _css.exists():
    st.markdown(f"<style>{_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# Example questions per dataset, so the suggestions match the active data.
EXAMPLES = {
    "olist": [
        "What are the top 10 product categories by revenue?",
        "What is our total revenue?",
        "How many customers do we have?",
        "What is the average delivery time in days?",
    ],
    "upi": [
        "What is the total transaction value by merchant category?",
        "What is the overall success rate?",
        "How many transactions were flagged as fraudulent?",
        "What is the total value of P2M transactions?",
    ],
    "starter": [
        "What is total revenue by product category?",
        "How many orders were placed in each status?",
    ],
}
examples = EXAMPLES.get(DATASET, EXAMPLES["starter"])

st.markdown(
    """
    <div class="hero">
      <span class="hero-badge">Schema-driven &middot; Measured</span>
      <div class="hero-title">Analytics <span class="grad">Agent</span></div>
      <div class="hero-sub">Ask a business question in plain English. The agent reads the
      schema, writes SQL, runs it, and explains the result &mdash; with a chart and the
      live token cost.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("#### Dataset")
    st.markdown(f'<span class="ds-pill">{DATASET}</span>', unsafe_allow_html=True)
    st.caption("Switch with the DATASET env var; the agent code does not change.")
    st.markdown("#### Try an example")
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["q"] = ex

q = st.text_input("Your question", st.session_state.get("q", examples[0]))
ask = st.button("Ask", type="primary")

if ask and q.strip():
    with st.spinner("Thinking..."):
        try:
            res = answer(q)

            with st.container(border=True):
                st.markdown('<div class="card-label">SQL</div>', unsafe_allow_html=True)
                st.code(res["sql"], language="sql")

            with st.container(border=True):
                st.markdown('<div class="card-label">Result</div>', unsafe_allow_html=True)
                st.dataframe(res["data"], use_container_width=True)
                fig = auto_chart(res["data"])
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)

            with st.container(border=True):
                st.markdown('<div class="card-label">Insight</div>', unsafe_allow_html=True)
                try:
                    st.markdown(md_safe(narrate(q, res["data"])))
                except Exception as e:
                    st.caption(f"Insight unavailable: {e}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Latency", f'{res["latency_s"]} s')
            c2.metric("Tokens in / out", f'{res["tokens_in"]} / {res["tokens_out"]}')
            c3.metric("Cost", f'Rs {res["cost_inr"]:.2f}')
        except Exception as e:
            st.error(f"Could not answer: {e}")
