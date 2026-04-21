"""Assistant configuration types."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssistantConfig:
    assistant_id: str
    display_name: str
    persona_paths: tuple[str, ...]
    knowledge_set_id: str
    scope_description: str
    denied_topics: tuple[str, ...] = field(default_factory=tuple)
