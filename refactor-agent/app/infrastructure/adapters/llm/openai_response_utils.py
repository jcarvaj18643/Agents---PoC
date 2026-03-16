import json
from typing import Any


def extract_output_text(response: Any) -> str:
    direct_output = _strip_text(getattr(response, "output_text", None))
    if direct_output:
        return direct_output

    if isinstance(response, dict):
        direct_dict_output = _strip_text(response.get("output_text"))
        if direct_dict_output:
            return direct_dict_output

    chunk_output = _extract_chunk_output(getattr(response, "output", None))
    if chunk_output:
        return chunk_output

    return ""


def extract_usage_tokens(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")

    if usage is None:
        return 0

    total_tokens = getattr(usage, "total_tokens", None)
    if isinstance(total_tokens, int):
        return total_tokens

    if isinstance(usage, dict):
        for key in ("total_tokens", "output_tokens", "input_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                return value

    return 0


def parse_json_object(output_text: str) -> dict[str, Any]:
    cleaned = output_text.strip()
    if not cleaned:
        return {}

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return {}


def _extract_chunk_output(output: Any) -> str:
    if not isinstance(output, list):
        return ""

    text_chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, list):
            continue
        for block in content:
            text = _strip_text(getattr(block, "text", None))
            if text:
                text_chunks.append(text)

    return "\n".join(text_chunks)


def _strip_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()