from typing import TypedDict


class NewsItem(TypedDict):
    title: str
    link: str
    published: str
    source: str
    summary: str