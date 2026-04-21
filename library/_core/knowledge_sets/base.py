"""Knowledge-set configuration types."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeSetConfig:
    knowledge_set_id: str
    display_name: str
    manifest_path: str
    db_path: str
    source_roots: tuple[str, ...] = field(default_factory=tuple)
