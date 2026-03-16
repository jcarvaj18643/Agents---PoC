import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ENV_FILE = _PROJECT_ROOT / ".env"


@dataclass
class Settings:
    """Centralised configuration loaded from environment variables.

    All environment access is confined here so the rest of the codebase
    remains testable without monkeypatching os.environ.
    """

    # LLM
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o")
    )

    # Directories
    policies_dir: Path = field(
        default_factory=lambda: Path(os.getenv("POLICIES_DIR", "policies"))
    )
    reports_dir: Path = field(
        default_factory=lambda: Path(os.getenv("REPORTS_DIR", "reports"))
    )

    # Agent behaviour
    dry_run: bool = field(
        default_factory=lambda: os.getenv("DRY_RUN", "true").lower() == "true"
    )
    max_suggestions_per_run: int = field(
        default_factory=lambda: int(os.getenv("MAX_SUGGESTIONS_PER_RUN", "10"))
    )
    enforce_public_api_guard: bool = field(
        default_factory=lambda: os.getenv("ENFORCE_PUBLIC_API_GUARD", "true").lower() == "true"
    )
    enable_lint_validation: bool = field(
        default_factory=lambda: os.getenv("ENABLE_LINT_VALIDATION", "true").lower() == "true"
    )
    enable_coverage_validation: bool = field(
        default_factory=lambda: os.getenv("ENABLE_COVERAGE_VALIDATION", "true").lower() == "true"
    )
    execute_validation_checks: bool = field(
        default_factory=lambda: os.getenv("EXECUTE_VALIDATION_CHECKS", "false").lower() == "true"
    )
    python_coverage_fail_under: int = field(
        default_factory=lambda: int(os.getenv("PYTHON_COVERAGE_FAIL_UNDER", "80"))
    )

    # GitHub (populated automatically in GitHub Actions runners)
    github_token: Optional[str] = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
    )
    github_api_base_url: str = field(
        default_factory=lambda: os.getenv("GITHUB_API_BASE_URL", "https://api.github.com")
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """Construct Settings by reading all values from the environment."""
        load_dotenv(dotenv_path=_DEFAULT_ENV_FILE, override=False)
        return cls()
