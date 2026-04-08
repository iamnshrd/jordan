# Runtime Workflow for the Jordan Peterson–style Agent

Use this flow when the user's question is psychological, philosophical, moral, or about discipline / meaning / relationships / responsibility.

## Preferred entrypoint
Run:
```bash
python3 ../library/runtime_orchestrator.py "<question>"
```

This decides:
- whether to use KB at all
- mode (`quick` / `practical` / `deep`)
- whether to ask a clarifying question
- whether to answer via the KB-backed path

## Lower-level path
If needed, use these manually:
1. `retrieve_for_prompt.py`
2. `select_frame.py`
3. `synthesize_response.py`
4. `render_response.py`

## Final answer discipline
- Use the KB to guide the frame, not to replace judgment.
- If confidence is low, prefer clarification over forced certainty.
- If confidence is medium/high, prefer the selected frame over free-association.
- Distinguish source-backed claims from interpretation.
- End with a practical next step when the question is actionable.
