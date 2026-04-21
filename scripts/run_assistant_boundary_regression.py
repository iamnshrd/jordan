#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from _helpers import emit_report, temp_store
from library._core.registry import (
    get_assistant, get_default_assistant, get_knowledge_set,
)
from library._core.runtime.orchestrator import (
    orchestrate, orchestrate_for_adapter, orchestrate_for_llm,
)


def main() -> None:
    with temp_store() as store:
        question = 'Я потерял смысл, дисциплину и направление'
        run_result = orchestrate(question, user_id='telegram:64001', store=store)
        prompt_result = orchestrate_for_llm(
            question, user_id='telegram:64002', store=store,
        )
        adapter_result = orchestrate_for_adapter(
            question, user_id='telegram:64003', store=store,
        )

        assistant = get_default_assistant()
        knowledge_set = get_knowledge_set(assistant.knowledge_set_id)
        explicit_assistant = get_assistant('jordan')

        results = [
            {
                'name': 'registry_returns_jordan_defaults',
                'pass': assistant.assistant_id == 'jordan'
                and explicit_assistant.assistant_id == 'jordan'
                and knowledge_set.knowledge_set_id == 'jordan-kb',
            },
            {
                'name': 'assistant_persona_and_knowledge_files_exist',
                'pass': all(Path(path).exists() for path in assistant.persona_paths)
                and Path(knowledge_set.manifest_path).exists()
                and Path(knowledge_set.db_path).exists(),
            },
            {
                'name': 'run_prompt_and_adapter_expose_same_boundary_ids',
                'pass': run_result.get('assistant_id') == 'jordan'
                and prompt_result.get('assistant_id') == 'jordan'
                and adapter_result.get('assistant_id') == 'jordan'
                and run_result.get('knowledge_set_id') == 'jordan-kb'
                and prompt_result.get('knowledge_set_id') == 'jordan-kb'
                and adapter_result.get('knowledge_set_id') == 'jordan-kb',
            },
        ]

        emit_report(
            results,
            samples={
                'assistant': {
                    'assistant_id': assistant.assistant_id,
                    'display_name': assistant.display_name,
                    'knowledge_set_id': assistant.knowledge_set_id,
                },
                'knowledge_set': {
                    'knowledge_set_id': knowledge_set.knowledge_set_id,
                    'manifest_path': knowledge_set.manifest_path,
                    'db_path': knowledge_set.db_path,
                },
            },
        )


if __name__ == '__main__':
    main()
