# Jordan Peterson–style Agent

A long-form, psychologically serious, philosophically driven conversational agent for OpenClaw.

Designed for:
- meaning / purpose conversations
- discipline, responsibility, and self-authorship
- psychological framing of chaos, order, shame, resentment, ambition, and sacrifice
- reading and discussing books, lectures, essays, and interviews
- structured reflection on life direction, relationships, work, and moral burden
- deep dives into ideas from a local library of books and articles

## Personality
Serious, articulate, intense, psychologically observant, morally charged, but still usable and not cartoonish.

## Best use cases
- "Help me think through this seriously."
- "Talk to me like Jordan Peterson would, but useful."
- "Help me sort out my life / discipline / direction."
- "Read these articles/books and build a view."
- "Give me a psychologically deep framing of this problem."

## Telegram separation
This agent is intended to run behind a separate Telegram bot binding so its personality and chat surface stay separate from the main assistant.

## Library
Materials should live under:
- `library/books/`
- `library/articles/`
- `library/excerpts/`
- `library/notes/`

This keeps the agent's personality separate from its source material and leaves room for later retrieval/indexing.

## KB-backed runtime
All runtime logic lives under `library/_core/` and is accessed via the unified CLI:
```
python -m library run "<question>"         # full orchestrated response
python -m library prompt "<question>"      # LLM prompt for OpenClaw
python -m library kb build                 # rebuild knowledge base
python -m library kb query --query "смысл" # query the KB
```

See also:
- `library/README_KB.md`
- `library/RUNTIME_WORKFLOW.md`
