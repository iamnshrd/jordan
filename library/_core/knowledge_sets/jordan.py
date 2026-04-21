"""Jordan knowledge-set binding."""
from __future__ import annotations

from library.config import ARTICLES, BOOKS, DB_PATH, MANIFEST, TEXTS
from library._core.knowledge_sets.base import KnowledgeSetConfig


JORDAN_KNOWLEDGE_SET = KnowledgeSetConfig(
    knowledge_set_id='jordan-kb',
    display_name='Jordan Knowledge Base',
    manifest_path=str(MANIFEST),
    db_path=str(DB_PATH),
    source_roots=(str(BOOKS), str(ARTICLES), str(TEXTS)),
)
