"""Pick a sensible default chart from the result shape. Returns a Plotly fig or None."""
import pandas as pd
import plotly.express as px

ACCENT = "#7C5CFF"


def _style(fig):
    """Dark, transparent styling so the chart sits on the app's dark theme."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E7E7EA",
        margin=dict(l=10, r=10, t=46, b=10),
    )
    return fig


def auto_chart(df):
    if df is None or df.empty or df.shape[1] < 2:
        return None
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return None
    y = numeric[-1]
    x = next((c for c in df.columns if c != y), None)
    if x is None:
        return None
    is_time = pd.api.types.is_datetime64_any_dtype(df[x]) or "date" in str(x).lower()
    if is_time:
        try:
            df = df.sort_values(x)
        except Exception:
            pass
        fig = px.line(df, x=x, y=y, title=f"{y} by {x}", markers=True)
        fig.update_traces(line_color=ACCENT, marker_color=ACCENT)
        return _style(fig)
    if len(df) <= 30:
        fig = px.bar(df, x=x, y=y, title=f"{y} by {x}")
        fig.update_traces(marker_color=ACCENT)
        return _style(fig)
    return None
