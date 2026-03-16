from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class DocumentationArtifact:
    """Output artifact produced by the documentation generation step.

    Carries the LLM-generated documentation for a single file, along with
    provenance metadata (model used, token usage, timestamp).
    """

    file_path: Path
    generated_content: str
    generated_at: datetime
    model_used: str
    tokens_used: int = 0
