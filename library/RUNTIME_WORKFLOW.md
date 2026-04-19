# Runtime Workflow

Use this flow when the question is psychological, philosophical, moral, or
about discipline, meaning, relationships, responsibility, shame, or resentment.

## Main Entrypoints

```bash
python -m library run "<question>"
python -m library prompt "<question>"
python -m library retrieve "<question>"
```

## Pipeline

The runtime is centered on `library/_core/runtime/`:

- `orchestrator.py` — top-level decision path
- `retrieve.py` — chunk, quote, and evidence retrieval
- `frame.py` — route and framing logic
- `synthesize.py` — grounded synthesis data
- `respond.py` — local rendering with strict grounding checks
- `llm_prompt.py` — OpenClaw/system prompt assembly

## Operating Rules

- Prefer KB-backed answers over free generation.
- If grounding is weak, ask a clarifying question instead of guessing.
- Distinguish DB-backed evidence from runtime interpretation.
- Treat `python -m library run` and `python -m library prompt` as the canonical execution paths.

## Related Docs

- [README_KB.md](/tmp/jordan/library/README_KB.md) — KB and CLI reference
- [CONTINUITY_WORKFLOW.md](/tmp/jordan/library/CONTINUITY_WORKFLOW.md) — continuity state notes
