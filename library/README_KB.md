# Jordan Knowledge Base

This is the SQLite-backed knowledge layer for the Jordan Peterson–style agent.

## Files
- `jordan_knowledge.db` — SQLite database
- `manifest.json` — registered source documents
- `build_kb.py` — build/import corpus into DB
- `query_kb.py` — query helper for chunks and taxonomy tables
- `texts/` — extracted plain text sources
- `books/`, `articles/`, `excerpts/`, `notes/` — source library

## Current schema
### Corpus
- `documents`
- `document_chunks`
- `document_chunks_fts`

### Distilled knowledge
- `themes`
- `principles`
- `patterns`
- `intervention_styles`
- `quotes`

## Planned schema expansion
To mirror the PMT-style layered setup more closely, future tables should include:
- `cases`
- `theme_evidence`
- `principle_evidence`
- `pattern_evidence`
- `argument_frames`
- `relationship_patterns`
- `developmental_problems`
- `symbolic_motifs`
- `intervention_examples`

## Typical workflow
1. Add PDF/text source to library
2. Extract text into `texts/`
3. Register/update `manifest.json`
4. Run `build_kb.py`
5. Query with `query_kb.py`
6. Later: extract distilled rows and evidence links

## Semi-automatic ingestion
New PDFs can be dropped into:
- `incoming/`

Then run:
```bash
python3 ingest_auto.py
```

This will:
- classify PDFs into `books/` or `articles/`
- extract text with `pdftotext`
- register them in `manifest.json`
- rebuild / refresh KB layers
- refresh quote extraction and quote loading
- write an ingestion report to `ingest_report.json`

## One-shot helper
You can also run:
```bash
bash ingest_new_file.sh /path/to/file.pdf
```
