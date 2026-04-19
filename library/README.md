# Library Layout

This directory contains both the package code and the local source material that
feeds the Jordan KB.

## Source Material Folders

- `books/` — full books or long-form texts
- `articles/` — essays, interviews, transcripts, and article-like inputs
- `excerpts/` — selected passages and clipped sections
- `notes/` — agent-authored or user-authored synthesis
- `incoming/` — raw newly added files before normalization
- `texts/` — extracted plain text used by KB build

## Suggested Material Flow

1. Drop new files into `incoming/`
2. Rename or normalize them
3. Move them into the correct source folder
4. Extract text into `texts/` when the KB should index them
5. Register them in `manifest.json`
6. Run `python -m library kb build`

## Canonical References

- [README_KB.md](/tmp/jordan/library/README_KB.md) — KB build/query reference
- [RUNTIME_WORKFLOW.md](/tmp/jordan/library/RUNTIME_WORKFLOW.md) — runtime overview
