from __future__ import annotations

import logging

from app.services.email_service import EmailService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: EmailService) -> AgentState:
    logger.info("node=send_email start")

    try:
        sent, error, executive_summary = service.send_executive_summary(state)
        if sent:
            logger.info("node=send_email done status=sent")
            return {
                "email_sent": True,
                "email_error": None,
                "executive_summary": executive_summary,
                "error": None,
            }

        warnings = list(state.get("warnings", []))
        if error:
            warnings.append(f"Email not sent: {error}")

        logger.info("node=send_email done status=skipped")
        return {
            "email_sent": False,
            "email_error": error,
            "executive_summary": executive_summary,
            "warnings": warnings,
            "error": None,
        }
    except Exception as exc:
        warnings = list(state.get("warnings", []))
        warnings.append(f"Email delivery failed: {exc}")
        logger.exception("node=send_email failed error=%s", exc)
        return {
            "email_sent": False,
            "email_error": str(exc),
            "warnings": warnings,
            "error": None,
        }
