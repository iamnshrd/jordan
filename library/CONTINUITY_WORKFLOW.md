# Conversation Continuity

Continuity is managed through `StateStore` and updated automatically during
`python -m library run`.

## What It Tracks

- recurring themes
- recurring user patterns
- open loops and unresolved burdens

## Main Code

- `library/_core/session/continuity.py`
- `library/_core/state_store.py`
- `library/_adapters/fs_store.py`

## Storage

The legacy local file path is `workspace/continuity.json`, but callers should
interact through the store layer rather than the file directly.

For the main runtime flow, see
[RUNTIME_WORKFLOW.md](/tmp/jordan/library/RUNTIME_WORKFLOW.md).
