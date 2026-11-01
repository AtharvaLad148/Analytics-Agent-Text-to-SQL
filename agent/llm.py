"""One place to build the Anthropic client, so every call site shares the same
provider config.

The key comes from ANTHROPIC_API_KEY. If ANTHROPIC_BASE_URL is set, requests go
through that gateway (e.g. FastRouter, which is Anthropic-Messages compatible and
accepts the x-api-key the SDK sends); if it is unset, the SDK talks to Anthropic
directly. That is the whole difference between a native key and a gateway key.
"""
from anthropic import Anthropic

from .config import BASE_URL


def new_client():
    return Anthropic(base_url=BASE_URL) if BASE_URL else Anthropic()


def message_text(resp):
    """Join the text blocks of a Messages response.

    Sonnet can return a thinking block before the text, so we cannot assume
    content[0] is text; take every text block and ignore the rest.
    """
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()
    if not text:
        raise ValueError("Model returned no text content.")
    return text
