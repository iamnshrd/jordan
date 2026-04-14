# Conversation Continuity Workflow

Use this to maintain personal continuity for the Jordan Peterson–style agent.

## Storage
Continuity data is managed via `StateStore` and persisted in `workspace/continuity.json`.

## Track
- recurring themes
- recurring user patterns
- open loops / unresolved burdens

## Usage
Continuity is automatically updated by the orchestrator during `python -m library run`.
The relevant logic lives in `library/_core/session/continuity.py`.

## When continuity updates
- when the same issue appears again
- when the user reveals a recurring burden
- when a theme/pattern becomes stable across multiple conversations
- when an unresolved loop should be remembered for future talks
