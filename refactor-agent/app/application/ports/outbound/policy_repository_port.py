from abc import ABC, abstractmethod
from typing import List

from app.domain.value_objects.engineering_policy import EngineeringPolicy


class PolicyRepositoryPort(ABC):
    """Outbound port — loads engineering policies applicable to a given project profile."""

    @abstractmethod
    def load_policies(self, profile_name: str) -> List[EngineeringPolicy]:
        ...
