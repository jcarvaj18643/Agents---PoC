from dataclasses import dataclass


@dataclass(frozen=True)
class GetRunStatusQuery:
    """Query to retrieve the status of a past (possibly async) agent run.

    Exists to support future async workflows where the orchestrator is
    non-blocking and the caller polls for completion.
    """

    run_id: str
