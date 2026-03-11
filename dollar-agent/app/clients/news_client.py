from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from app.config import settings
from app.utils.text_cleaner import normalize_whitespace


class NewsClient:
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
    GLOBAL_MACRO_RSS_FEEDS = (
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    )

    def _parse_pub_date(self, value: str) -> datetime | None:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _normalize_item(self, item: ET.Element) -> dict[str, str]:
        title = normalize_whitespace((item.findtext("title") or ""))
        link = normalize_whitespace((item.findtext("link") or ""))
        pub_date = normalize_whitespace((item.findtext("pubDate") or ""))
        description = normalize_whitespace((item.findtext("description") or ""))

        source_name = ""
        source = item.find("source")
        if source is not None and source.text:
            source_name = normalize_whitespace(source.text)

        return {
            "title": title,
            "link": link,
            "published": pub_date,
            "summary": description,
            "source": source_name,
        }

    def _fetch_rss(self, url: str) -> ET.Element | None:
        try:
            response = requests.get(url, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            return ET.fromstring(response.text)
        except (requests.RequestException, ET.ParseError):
            return None

    def _collect_recent_items(self, root: ET.Element, max_items: int) -> list[tuple[datetime, dict[str, str]]]:
        channel = root.find("channel")
        if channel is None:
            return []

        cutoff = datetime.now(UTC) - timedelta(days=settings.max_news_age_days)
        items_with_date: list[tuple[datetime, dict[str, str]]] = []

        for item in channel.findall("item")[:max_items]:
            normalized_item = self._normalize_item(item)
            pub_date = normalized_item.get("published", "")
            if not pub_date:
                continue

            parsed_utc = self._parse_pub_date(pub_date)
            if parsed_utc is None or parsed_utc < cutoff:
                continue

            items_with_date.append((parsed_utc, normalized_item))

        return items_with_date

    def fetch_global_macro_news(self, max_items: int) -> list[dict[str, str]]:
        # Keep only globally relevant macro/FX items to enrich sparse local coverage.
        include_tokens = (
            "oil",
            "brent",
            "wti",
            "fed",
            "federal reserve",
            "dollar",
            "dxy",
            "treasury",
            "yield",
            "inflation",
            "rates",
            "risk",
            "vix",
            "emerging market",
        )

        merged: list[tuple[datetime, dict[str, str]]] = []
        for feed_url in self.GLOBAL_MACRO_RSS_FEEDS:
            root = self._fetch_rss(feed_url)
            if root is None:
                continue
            merged.extend(self._collect_recent_items(root, max_items=max_items))

        dedup: list[tuple[datetime, dict[str, str]]] = []
        seen_titles: set[str] = set()
        for published_at, item in sorted(merged, key=lambda x: x[0], reverse=True):
            title_key = item.get("title", "").strip().lower()
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            if not title_key or title_key in seen_titles:
                continue
            if not any(token in text for token in include_tokens):
                continue
            seen_titles.add(title_key)
            dedup.append((published_at, item))
            if len(dedup) >= max_items:
                break

        return [item for _, item in dedup]

    def search(self, query: str, max_items: int) -> list[dict[str, str]]:
        encoded_query = quote_plus(query)
        url = (
            f"{self.GOOGLE_NEWS_RSS}?q={encoded_query}"
            "&hl=en-US&gl=US&ceid=US:en"
        )

        root = self._fetch_rss(url)
        if root is None:
            return []

        items_with_date = self._collect_recent_items(root, max_items=max_items)

        items_with_date.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in items_with_date]
