# Runtime Workflow for the Jordan Peterson–style Agent

Use this flow when the user's question is psychological, philosophical, moral, or about discipline / meaning / relationships / responsibility.

## Entrypoint
```bash
python -m library run "<question>"       # full orchestrated response
python -m library prompt "<question>"    # LLM prompt for OpenClaw
```

This decides:
- whether to use KB at all
- mode (`quick` / `practical` / `deep`)
- whether to ask a clarifying question
- whether to answer via the KB-backed path
- retrieval validation (relevance check)

## Other commands
```bash
python -m library frame "<question>"                       # select psychological frame
python -m library respond "<question>" --mode deep --voice hard  # generate response
python -m library retrieve "<question>"                    # build response bundle
```

## Architecture
All runtime logic lives in `library/_core/runtime/`:
- `orchestrator.py` — main pipeline (orchestrate / orchestrate_for_llm)
- `retrieve.py` — FTS + hybrid retrieval, evidence ranking
- `frame.py` — frame selection
- `synthesize.py` — response synthesis
- `respond.py` — rendering
- `llm_prompt.py` — LLM prompt assembly for OpenClaw
- `retrieval_validator.py` — relevance validation
- `voice.py` — voice mode selection

## Final answer discipline
- Use the KB to guide the frame, not to replace judgment.
- If confidence is low, prefer clarification over forced certainty.
- If confidence is medium/high, prefer the selected frame over free-association.
- Distinguish source-backed claims from interpretation.
- End with a practical next step when the question is actionable.
