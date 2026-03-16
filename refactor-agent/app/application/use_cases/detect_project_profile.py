from app.application.ports.outbound.project_structure_reader_port import (
    ProjectStructureReaderPort,
)
from app.domain.value_objects.project_profile import ProjectProfile


class DetectProjectProfileUseCase:
    """Use case: determine the project's technology profile from its file structure.

    The profile drives which engineering policies are loaded and which LLM prompts
    are constructed. Heuristics and confidence scoring will be added here.
    """

    def __init__(self, structure_reader: ProjectStructureReaderPort) -> None:
        self._structure_reader = structure_reader

    def execute(self, repo_path: str) -> ProjectProfile:
        # TODO: add confidence scoring and fallback profile logic
        return self._structure_reader.read_structure(repo_path)
