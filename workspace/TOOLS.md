# Tools

Keep source material in `../library/`.
If books or articles are added, prefer clean filenames and stable organization.

## KB Runtime Helpers

Preferred integrated helper:
- `../library/runtime_orchestrator.py`

Secondary integrated helper:
- `../library/respond_with_kb.py`

Lower-level helpers:
- `../library/retrieve_for_prompt.py`
- `../library/select_frame.py`
- `../library/synthesize_response.py`
- `../library/render_response.py`
- `../library/update_continuity.py`

## Unified CLI

All operations are also available via:

```bash
python -m library run "вопрос"
python -m library respond "вопрос" --mode deep --voice hard
python -m library frame "вопрос"
python -m library kb build
python -m library kb query --query "смысл"
python -m library ingest auto
python -m library eval audit
```

## Architecture

The legacy wrapper scripts (e.g. `runtime_orchestrator.py`) delegate to the
refactored package at `library/_core/`. All paths are defined in
`library/config.py` relative to the project root, so the project works on
any deployment location without path changes.
