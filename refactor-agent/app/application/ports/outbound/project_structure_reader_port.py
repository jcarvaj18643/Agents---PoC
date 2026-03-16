from abc import ABC, abstractmethod

from app.domain.value_objects.project_profile import ProjectProfile


class ProjectStructureReaderPort(ABC):
    """Outbound port — inspects the repository file system to determine the project profile."""

    @abstractmethod
    def read_structure(self, repo_path: str) -> ProjectProfile:
        ...
