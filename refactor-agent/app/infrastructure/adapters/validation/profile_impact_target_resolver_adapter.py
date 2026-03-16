from pathlib import Path

from app.application.ports.outbound.impact_target_resolver_port import (
    ImpactTargetResolverPort,
)
from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution
from app.domain.value_objects.project_profile import ProjectProfile
from app.infrastructure.adapters.validation.angular_impact_target_resolver_adapter import (
    AngularImpactTargetResolverAdapter,
)
from app.infrastructure.adapters.validation.csharp_impact_target_resolver_adapter import (
    CSharpImpactTargetResolverAdapter,
)
from app.infrastructure.adapters.validation.python_impact_target_resolver_adapter import (
    PythonImpactTargetResolverAdapter,
)


class ProfileImpactTargetResolverAdapter(ImpactTargetResolverPort):
    """Dispatch stack-specific target resolution behind a single outbound port."""

    def __init__(
        self,
        python_resolver: PythonImpactTargetResolverAdapter | None = None,
        csharp_resolver: CSharpImpactTargetResolverAdapter | None = None,
        angular_resolver: AngularImpactTargetResolverAdapter | None = None,
    ) -> None:
        self._python_resolver = python_resolver or PythonImpactTargetResolverAdapter()
        self._csharp_resolver = csharp_resolver or CSharpImpactTargetResolverAdapter()
        self._angular_resolver = angular_resolver or AngularImpactTargetResolverAdapter()

    def resolve(
        self,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ImpactTargetResolution:
        repo_root = Path(repo_path)
        if profile.language == "python":
            return self._python_resolver.resolve(repo_root, changed_files)
        if profile.language == "csharp":
            return self._csharp_resolver.resolve(repo_root, changed_files)
        if profile.language == "typescript" and profile.framework == "angular":
            return self._angular_resolver.resolve(repo_root, changed_files)
        return ImpactTargetResolution(working_directory=repo_root)