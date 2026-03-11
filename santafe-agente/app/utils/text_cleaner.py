import html
import re


def clean_html(raw_html: str) -> str:
    """
    Remove HTML tags and decode HTML entities.
    """
    if not raw_html:
        return ""

    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    return text.strip()