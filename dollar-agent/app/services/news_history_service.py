from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.config import settings
from app.utils.runtime_paths import project_root


class NewsHistoryService:
    def __init__(self) -> None:
        self.storage_path = project_root() / "data" / "history" / "news_history.json"

    def _read_entries(self) -> list[dict[str, str]]:
        if not self.storage_path.exists():
            return []

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(payload, dict):
            return []

        entries = payload.get("news")
        if not isinstance(entries, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in entries:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "title": str(item.get("title", "")),
                        "link": str(item.get("link", "")),
                        "published": str(item.get("published", "")),
                        "summary": str(item.get("summary", "")),
                        "source": str(item.get("source", "")),
                        "stored_at": str(item.get("stored_at", "")),
                    }
                )
        return normalized

    def _write_entries(self, entries: list[dict[str, str]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"news": entries}
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _is_recent(self, stored_at: str, cutoff: datetime) -> bool:
        if not stored_at:
            return False
        try:
            parsed = datetime.fromisoformat(stored_at.replace("Z", "+00:00"))
        except ValueError:
            return False

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC) >= cutoff

    def _published_sort_value(self, value: str) -> datetime:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime(1970, 1, 1, tzinfo=UTC)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def merge_with_recent_history(self, fresh_news: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=settings.history_window_days)

        history_entries = [
            item for item in self._read_entries() if self._is_recent(item.get("stored_at", ""), cutoff)
        ]

        merged: list[dict[str, str]] = []
        seen_titles: set[str] = set()
        historical_used = 0

        for item in fresh_news:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            merged.append(
                {
                    "title": title,
                    "link": str(item.get("link", "")),
                    "published": str(item.get("published", "")),
                    "summary": str(item.get("summary", "")),
                    "source": str(item.get("source", "")),
                    "stored_at": now.isoformat(),
                }
            )

        for old_item in history_entries:
            title = str(old_item.get("title", "")).strip()
            if not title:
                continue
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            historical_used += 1
            merged.append(old_item)

        merged.sort(
            key=lambda x: self._published_sort_value(x.get("published", "")),
            reverse=True,
        )

        self._write_entries(merged)

        result = [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "published": item.get("published", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
            }
            for item in merged
        ]
        return result, historical_used
