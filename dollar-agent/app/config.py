from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from app.utils.runtime_paths import dotenv_file

load_dotenv(dotenv_path=dotenv_file(), override=False)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    sendgrid_api_key: str | None
    openai_model: str
    default_user_query: str
    default_analysis_horizon: str
    default_output_language: str
    max_news_items: int
    max_news_age_days: int
    history_window_days: int
    max_retries: int
    request_timeout_seconds: int
    run_start_hour: int
    run_end_hour: int
    send_email_enabled: bool
    send_email_hours: tuple[int, ...]
    sendgrid_from_email: str
    sendgrid_to_email: str
    sendgrid_from_name: str
    sendgrid_subject_prefix: str


settings = Settings(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    sendgrid_api_key=os.getenv("SENDGRID_API_KEY"),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    default_user_query=os.getenv(
        "DEFAULT_USER_QUERY",
        "What is the likely short-term direction of USD/COP?",
    ),
    default_analysis_horizon=os.getenv("DEFAULT_ANALYSIS_HORIZON", "1-2 weeks"),
    default_output_language=os.getenv("DEFAULT_OUTPUT_LANGUAGE", "spanish"),
    max_news_items=int(os.getenv("MAX_NEWS_ITEMS", "12")),
    max_news_age_days=int(os.getenv("MAX_NEWS_AGE_DAYS", "7")),
    history_window_days=int(os.getenv("HISTORY_WINDOW_DAYS", "5")),
    max_retries=int(os.getenv("MAX_RETRIES", "2")),
    request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "12")),
    run_start_hour=max(0, min(23, int(os.getenv("RUN_START_HOUR", "8")))),
    run_end_hour=max(0, min(23, int(os.getenv("RUN_END_HOUR", "17")))),
    send_email_enabled=os.getenv("SEND_EMAIL_ENABLED", "true").strip().lower() in {"1", "true", "yes"},
    send_email_hours=tuple(
        hour
        for hour in (
            int(token.strip())
            for token in os.getenv("SEND_EMAIL_HOURS", "8,17").split(",")
            if token.strip().isdigit()
        )
        if 0 <= hour <= 23
    ) or (8, 17),
    sendgrid_from_email=os.getenv("SENDGRID_FROM_EMAIL", ""),
    sendgrid_to_email=os.getenv("SENDGRID_TO_EMAIL", ""),
    sendgrid_from_name=os.getenv("SENDGRID_FROM_NAME", "USD/COP Analysis Agent"),
    sendgrid_subject_prefix=os.getenv("SENDGRID_SUBJECT_PREFIX", "USD/COP Executive Summary"),
)
