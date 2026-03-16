from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepositoryPromptGuidance:
    """Structured repository-level guidance injected into LLM prompts."""

    source_path: str | None = None
    repository_name: str | None = None
    framework: str | None = None
    architecture: str | None = None
    summary: str | None = None
    design_principles: tuple[str, ...] = field(default_factory=tuple)
    layer_conventions: tuple[str, ...] = field(default_factory=tuple)
    refactor_guardrails: tuple[str, ...] = field(default_factory=tuple)
    naming_conventions: tuple[str, ...] = field(default_factory=tuple)
    additional_instructions: tuple[str, ...] = field(default_factory=tuple)

    def to_prompt_block(self) -> str:
        lines: list[str] = []
        if self.repository_name:
            lines.append(f"Repository name: {self.repository_name}")
        if self.framework:
            lines.append(f"Framework or platform: {self.framework}")
        if self.architecture:
            lines.append(f"Architecture: {self.architecture}")
        if self.summary:
            lines.append(f"Repository summary: {self.summary}")
        lines.extend(self._format_list("Design principles", self.design_principles))
        lines.extend(self._format_list("Layer conventions", self.layer_conventions))
        lines.extend(self._format_list("Refactor guardrails", self.refactor_guardrails))
        lines.extend(self._format_list("Naming conventions", self.naming_conventions))
        lines.extend(self._format_list("Additional instructions", self.additional_instructions))
        return "\n".join(lines)

    def _format_list(self, title: str, items: tuple[str, ...]) -> list[str]:
        if not items:
            return []
        return [f"{title}:", *[f"- {item}" for item in items]]