from __future__ import annotations

from app.state import AgentState


class FallbackService:
    def can_retry(self, state: AgentState) -> bool:
        return state.get("retry_count", 0) < state.get("max_retries", 0)

    def mark_retry(self, state: AgentState, reason: str) -> AgentState:
        warnings = list(state.get("warnings", []))
        warnings.append(f"Retry activated: {reason}")

        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "fallback_reason": reason,
            "warnings": warnings,
        }

    def mark_degraded(self, state: AgentState, reason: str) -> AgentState:
        warnings = list(state.get("warnings", []))
        warnings.append(f"Degraded mode: {reason}")

        return {
            "degraded_mode": True,
            "confidence_level": "low",
            "fallback_reason": reason,
            "warnings": warnings,
        }
