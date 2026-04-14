# Tools

Keep source material in `../library/`.
If books or articles are added, prefer clean filenames and stable organization.

## Unified CLI

All operations are available via:

```bash
python -m library run "вопрос"                            # full orchestrated response
python -m library prompt "вопрос"                          # LLM prompt for OpenClaw
python -m library respond "вопрос" --mode deep --voice hard
python -m library frame "вопрос"
python -m library retrieve "вопрос"
python -m library kb build
python -m library kb query --query "смысл"
python -m library ingest auto
python -m library eval audit
python -m library eval regression
python -m library eval full
```

## Architecture

All logic lives in the `library/_core/` package:
- `runtime/` — orchestrator, retrieval, frame selection, synthesis, LLM prompt, voice
- `kb/` — knowledge base: build, extract, normalize, evidence, quotes, seed, migrate, embeddings
- `session/` — continuity, state, progress, checkpoints, effectiveness
- `eval/` — audit, regression, evaluation
- `ingest/` — auto-ingest, book registration, epub conversion

Infrastructure in `library/`:
- `config.py` — paths and settings
- `db.py` — SQLite connection and helpers
- `utils.py` — shared utilities (JSON, FTS query, timing)
- `logging_config.py` — structured logging
