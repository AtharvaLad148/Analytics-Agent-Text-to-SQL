"""Turn a query result into a short product-analyst insight + recommendation."""
from .config import MODEL
from .llm import new_client, message_text

SYSTEM = (
    "You are a product analyst. Given a question and the query result, write 2 to 3 "
    "sentences: first the key insight using the actual numbers, then one concrete "
    "recommendation or next action. Be specific. No preamble, no bullet points."
)


def narrate(question, df, client=None):
    client = client or new_client()
    preview = df.head(20).to_markdown(index=False)
    resp = client.messages.create(
        model=MODEL,
        # Generous headroom: Sonnet 5.5 thinks by default, and those tokens count
        # against max_tokens, so a tight budget can leave no room for the answer.
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Question: {question}\n\nResult:\n{preview}"}],
    )
    return message_text(resp)
