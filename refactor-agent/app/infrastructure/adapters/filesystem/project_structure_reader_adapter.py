from pathlib import Path
from typing import Iterable, Optional

from app.application.ports.outbound.project_structure_reader_port import (
    ProjectStructureReaderPort,
)
from app.domain.value_objects.project_profile import ProjectProfile
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

ANGULAR_CONFIG = "angular.json"
CSPROJ_GLOB = "*.csproj"
SOLUTION_GLOB = "*.sln"
IGNORED_SOURCE_DIRS = {
    ".angular",
    ".git",
    ".scannerwork",
    "__pycache__",
    "agent_env",
    "coverage",
    "dist",
    "node_modules",
}

# Heuristic markers per language
_LANGUAGE_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"],
    "csharp": ["global.json"],
    "javascript": ["package.json"],
    "typescript": ["tsconfig.json"],
    "java": ["pom.xml", "build.gradle"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
}


class ProjectStructureReaderAdapter(ProjectStructureReaderPort):
    """Adapter: detects the project profile by inspecting well-known marker files."""

    def read_structure(self, repo_path: str) -> ProjectProfile:
        logger.info("Detecting project profile for: %s", repo_path)
        root = Path(repo_path)

        detected_patterns = tuple(self._detect_patterns(root))
        detected_language = self._detect_language(root)
        framework = self._detect_framework(root, detected_language)
        test_framework = self._detect_test_framework(root, detected_language)
        has_type_hints = self._detect_type_hints(root, detected_language)

        return ProjectProfile(
            name=self._build_profile_name(detected_language, framework),
            language=detected_language,
            framework=framework,
            test_framework=test_framework,
            has_type_hints=has_type_hints,
            detected_patterns=detected_patterns,
        )

    def _detect_patterns(self, root: Path) -> list[str]:
        patterns: list[str] = []
        for language, markers in _LANGUAGE_MARKERS.items():
            for marker in markers:
                if (root / marker).exists():
                    patterns.append(f"marker:{language}:{marker}")
        if (root / "tests").exists():
            patterns.append("dir:tests")
        if (root / "conftest.py").exists():
            patterns.append("file:conftest.py")
        if any(root.glob("vite.config.*")):
            patterns.append("file:vite.config")
        if (root / ANGULAR_CONFIG).exists():
            patterns.append("file:angular.json")
        if self._has_csharp_project_markers(root):
            patterns.append("file:csharp-project")
        if (root / "next.config.js").exists() or (root / "next.config.mjs").exists():
            patterns.append("file:next.config")
        return patterns

    def _detect_language(self, root: Path) -> str:
        if self._has_csharp_project_markers(root) or self._has_source_file(root, ".cs"):
            return "csharp"
        if (root / "tsconfig.json").exists():
            return "typescript"
        for language, markers in _LANGUAGE_MARKERS.items():
            if any((root / marker).exists() for marker in markers):
                return language
        if self._has_source_file(root, ".py"):
            return "python"
        if self._has_source_file(root, ".cs"):
            return "csharp"
        if self._has_source_file(root, ".ts") or self._has_source_file(root, ".tsx"):
            return "typescript"
        if self._has_source_file(root, ".js") or self._has_source_file(root, ".jsx"):
            return "javascript"
        return "unknown"

    def _detect_framework(self, root: Path, language: str) -> Optional[str]:
        project_text = self._load_project_text(root)
        if language == "python":
            return self._detect_python_framework(root, project_text)
        if language == "csharp":
            return self._detect_csharp_framework(root, project_text)
        if language in {"javascript", "typescript"}:
            return self._detect_javascript_framework(root, project_text)
        return None

    def _detect_python_framework(self, root: Path, project_text: str) -> Optional[str]:
        if (root / "manage.py").exists() or "django" in project_text:
            return "django"
        if "fastapi" in project_text:
            return "fastapi"
        if "flask" in project_text:
            return "flask"
        return None

    def _detect_javascript_framework(self, root: Path, project_text: str) -> Optional[str]:
        if (root / ANGULAR_CONFIG).exists() or '"@angular/core"' in project_text:
            return "angular"
        if (root / "next.config.js").exists() or (root / "next.config.mjs").exists() or '"next"' in project_text:
            return "nextjs"
        if any(root.glob("vite.config.*")) or '"vite"' in project_text:
            return "vite"
        if '"react"' in project_text:
            return "react"
        return None

    def _detect_csharp_framework(self, root: Path, project_text: str) -> Optional[str]:
        if "microsoft.aspnetcore" in project_text or self._has_named_source_file(root, "Program.cs"):
            return "aspnetcore"
        return None

    def _detect_test_framework(self, root: Path, language: str) -> Optional[str]:
        project_text = self._load_project_text(root)
        if language == "python":
            return self._detect_python_test_framework(root, project_text)
        if language == "csharp":
            return self._detect_csharp_test_framework(project_text)
        if language in {"javascript", "typescript"}:
            return self._detect_javascript_test_framework(project_text)
        return None

    def _detect_python_test_framework(self, root: Path, project_text: str) -> Optional[str]:
        if (root / "pytest.ini").exists() or (root / "conftest.py").exists() or "pytest" in project_text:
            return "pytest"
        if (root / "tests").exists():
            return "unittest"
        return None

    def _detect_csharp_test_framework(self, project_text: str) -> Optional[str]:
        if "xunit" in project_text:
            return "xunit"
        if "nunit" in project_text:
            return "nunit"
        if "mstest" in project_text:
            return "mstest"
        return None

    def _detect_javascript_test_framework(self, project_text: str) -> Optional[str]:
        if '"vitest"' in project_text:
            return "vitest"
        if '"jest"' in project_text:
            return "jest"
        return None

    def _detect_type_hints(self, root: Path, language: str) -> bool:
        if language != "python":
            return language in {"typescript", "csharp"}

        python_files = list(self._iter_python_files(root))[:50]
        for python_file in python_files:
            try:
                content = python_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if "->" in content or ": " in content:
                return True
        return False

    def _iter_python_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*.py"):
            if self._should_skip_path(path):
                continue
            yield path

    def _iter_source_files(self, root: Path, pattern: str) -> Iterable[Path]:
        for path in root.rglob(pattern):
            if self._should_skip_path(path):
                continue
            yield path

    def _has_source_file(self, root: Path, suffix: str) -> bool:
        return any(self._iter_source_files(root, f"*{suffix}"))

    def _has_named_source_file(self, root: Path, file_name: str) -> bool:
        return any(self._iter_source_files(root, file_name))

    def _should_skip_path(self, path: Path) -> bool:
        if any(part in IGNORED_SOURCE_DIRS for part in path.parts):
            return True
        return any(part.startswith(".") for part in path.parts)

    def _load_project_text(self, root: Path) -> str:
        texts: list[str] = []
        for file_name in ("pyproject.toml", "requirements.txt", "package.json"):
            path = root / file_name
            if path.exists():
                try:
                    texts.append(path.read_text(encoding="utf-8").lower())
                except OSError:
                    continue
        for csproj_path in root.glob("*.csproj"):
            try:
                texts.append(csproj_path.read_text(encoding="utf-8").lower())
            except OSError:
                continue
        angular_json = root / ANGULAR_CONFIG
        if angular_json.exists():
            try:
                texts.append(angular_json.read_text(encoding="utf-8").lower())
            except OSError:
                pass
        return "\n".join(texts)

    def _has_csharp_project_markers(self, root: Path) -> bool:
        return any(root.glob(CSPROJ_GLOB)) or any(root.glob(SOLUTION_GLOB))

    def _build_profile_name(self, language: str, framework: Optional[str]) -> str:
        if framework:
            return f"{language}-{framework}"
        return language
