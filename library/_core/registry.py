"""Runtime registry for assistants and knowledge sets."""
from __future__ import annotations

from library._core.assistants.base import AssistantConfig
from library._core.assistants.jordan import JORDAN_ASSISTANT
from library._core.knowledge_sets.base import KnowledgeSetConfig
from library._core.knowledge_sets.jordan import JORDAN_KNOWLEDGE_SET


_ASSISTANTS = {
    JORDAN_ASSISTANT.assistant_id: JORDAN_ASSISTANT,
}

_KNOWLEDGE_SETS = {
    JORDAN_KNOWLEDGE_SET.knowledge_set_id: JORDAN_KNOWLEDGE_SET,
}


def get_assistant(assistant_id: str = 'jordan') -> AssistantConfig:
    return _ASSISTANTS.get(assistant_id, JORDAN_ASSISTANT)


def get_default_assistant() -> AssistantConfig:
    return JORDAN_ASSISTANT


def get_knowledge_set(knowledge_set_id: str = 'jordan-kb') -> KnowledgeSetConfig:
    return _KNOWLEDGE_SETS.get(knowledge_set_id, JORDAN_KNOWLEDGE_SET)
