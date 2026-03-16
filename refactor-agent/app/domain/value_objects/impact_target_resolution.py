from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ImpactTargetResolution:
    """Resolved validation targets for the changed scope of a specific repository."""

    working_directory: Path
    lint_targets: list[str] = field(default_factory=list)
    test_targets: list[str] = field(default_factory=list)
    owner_projects: list[str] = field(default_factory=list)
    module_owners: list[str] = field(default_factory=list)