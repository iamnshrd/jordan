# Jordan Peterson-style Agent

A long-form, psychologically serious conversational agent for OpenClaw.

Best suited for:
- meaning, direction, and vocation
- discipline, responsibility, and self-authorship
- shame, resentment, truth, and relationship maintenance
- reading and discussing books, lectures, essays, and interviews

## Quick Start

```bash
python -m library run "<question>"
python -m library prompt "<question>"
python -m library kb build
python -m library kb doctor
```

## Project Layout

- `library/` — package code, KB assets, source material, and CLI entrypoint
- `library/_core/` — runtime, KB, mentor, eval, and session logic
- `scripts/` — regression and smoke runners
- `workspace/` — local runtime state

## Docs

- [library/README_KB.md](/tmp/jordan/library/README_KB.md) — canonical KB and CLI reference
- [library/RUNTIME_WORKFLOW.md](/tmp/jordan/library/RUNTIME_WORKFLOW.md) — runtime pipeline overview
- [library/README.md](/tmp/jordan/library/README.md) — source material layout

## Notes

- This agent is intended to run behind a separate Telegram bot binding.
- Source material belongs in the library; prompt personality should not carry the corpus by itself.
