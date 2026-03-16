from typing import List

from app.application.ports.outbound.policy_repository_port import PolicyRepositoryPort
from app.domain.value_objects.engineering_policy import EngineeringPolicy


class LoadEngineeringPoliciesUseCase:
    """Use case: load the set of engineering policies applicable to a project profile.

    Policies are matched by profile name and will later support priority ordering,
    merging, and override mechanisms.
    """

    def __init__(self, policy_repository: PolicyRepositoryPort) -> None:
        self._policy_repository = policy_repository

    def execute(self, profile_name: str) -> List[EngineeringPolicy]:
        policies = self._policy_repository.load_policies(profile_name)
        deduplicated: dict[str, EngineeringPolicy] = {}
        for policy in policies:
            deduplicated[policy.id] = policy
        return list(deduplicated.values())
