"""Jordan assistant registry entry."""
from __future__ import annotations

from library.config import PROJECT
from library._core.assistants.base import AssistantConfig


JORDAN_ASSISTANT = AssistantConfig(
    assistant_id='jordan',
    display_name='Jordan',
    persona_paths=(
        str(PROJECT / 'IDENTITY.md'),
        str(PROJECT / 'SOUL.md'),
    ),
    knowledge_set_id='jordan-kb',
    scope_description=(
        'Psychological, moral, existential, relationship, discipline, and '
        'meaning-oriented questions grounded in the Jordan knowledge base.'
    ),
    denied_topics=(
        'shopping',
        'weather',
        'news',
        'technical-help',
        'medical-advice',
        'legal-financial-advice',
    ),
)
