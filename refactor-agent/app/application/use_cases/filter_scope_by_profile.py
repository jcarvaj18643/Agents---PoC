from fnmatch import fnmatch
from pathlib import Path

from app.domain.entities.code_scope import CodeScope
from app.domain.enums.language import Language
from app.domain.value_objects.project_profile import ProjectProfile
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_PYTHON_CONFIG_PATTERNS = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-*.txt",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "mypy.ini",
    ".ruff.toml",
    "ruff.toml",
    ".flake8",
    ".python-version",
    "pdm.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "uv.lock",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
}

_CSHARP_CONFIG_PATTERNS = {
    "*.csproj",
    "*.sln",
    "*.props",
    "*.targets",
    "*.runsettings",
    "appsettings.json",
    "appsettings.*.json",
    "web.config",
    "app.config",
    "nuget.config",
    "Directory.Build.props",
    "Directory.Build.targets",
    "packages.lock.json",
    "global.json",
}

_ANGULAR_CONFIG_PATTERNS = {
    "angular.json",
    "package.json",
    "tsconfig.json",
    "tsconfig.*.json",
    "karma.conf.js",
    "proxy.conf.json",
    "proxy.conf.*.json",
    ".browserslistrc",
    "browserslist",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    "eslint.config.js",
    ".prettierrc",
    ".prettierrc.json",
}


class FilterScopeByProfileUseCase:
    """Restrict the analyzed scope to files relevant to the detected stack."""

    def execute(self, scope: CodeScope, profile: ProjectProfile) -> CodeScope:
        allowed_languages = self._resolve_allowed_languages(profile)
        allowed_patterns = self._resolve_allowed_patterns(profile)
        filtered_files = []

        for changed_file in scope.changed_files:
            if not self._is_allowed_file(changed_file.path, changed_file.language, allowed_languages, allowed_patterns):
                logger.info(
                    "Skipping file outside profile language scope [%s]: %s (%s)",
                    profile.name,
                    changed_file.path,
                    changed_file.language.value,
                )
                continue
            filtered_files.append(changed_file)

        return CodeScope(
            changed_files=filtered_files,
            changed_symbols=list(scope.changed_symbols),
            base_ref=scope.base_ref,
            head_ref=scope.head_ref,
        )

    def _resolve_allowed_languages(self, profile: ProjectProfile) -> set[Language]:
        if profile.language == "python":
            return {Language.PYTHON, Language.SQL}
        if profile.language == "csharp":
            return {Language.CSHARP, Language.SQL}
        if profile.language == "typescript" and profile.framework == "angular":
            return {Language.TYPESCRIPT, Language.HTML, Language.SCSS}
        if profile.language in {"java", "go", "rust"}:
            return {Language(profile.language), Language.SQL}
        if profile.language == "typescript":
            return {Language.TYPESCRIPT}
        if profile.language == "javascript":
            return {Language.JAVASCRIPT}
        return {Language.UNKNOWN}

    def _resolve_allowed_patterns(self, profile: ProjectProfile) -> set[str]:
        if profile.language == "python":
            return _PYTHON_CONFIG_PATTERNS
        if profile.language == "csharp":
            return _CSHARP_CONFIG_PATTERNS
        if profile.language == "typescript" and profile.framework == "angular":
            return _ANGULAR_CONFIG_PATTERNS
        return set()

    def _is_allowed_file(
        self,
        path: Path,
        language: Language,
        allowed_languages: set[Language],
        allowed_patterns: set[str],
    ) -> bool:
        if language in allowed_languages:
            return True

        path_as_posix = path.as_posix()
        file_name = path.name
        return any(
            fnmatch(file_name, pattern) or fnmatch(path_as_posix, pattern)
            for pattern in allowed_patterns
        )