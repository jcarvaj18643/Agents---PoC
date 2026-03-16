from enum import Enum


class ChangeType(str, Enum):
    """The kind of change applied to a file or symbol in a git diff."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
