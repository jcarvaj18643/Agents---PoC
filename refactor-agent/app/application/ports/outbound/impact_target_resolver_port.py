from abc import ABC, abstractmethod

from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution
from app.domain.value_objects.project_profile import ProjectProfile


class ImpactTargetResolverPort(ABC):
    """Outbound port — resolves the smallest validation targets for a scoped change set."""

    @abstractmethod
    def resolve(
        self,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ImpactTargetResolution:
        ...