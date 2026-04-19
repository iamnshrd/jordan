# Jordan Knowledge Base

This is the SQLite-backed knowledge layer for the Jordan Peterson–style agent.

## Structure
- `jordan_knowledge.db` — SQLite database
- `manifest.json` — registered source documents
- `texts/` — extracted plain text sources
- `books/`, `articles/`, `excerpts/`, `notes/` — source library

## CLI
```bash
python -m library kb build                         # build/import corpus into DB
python -m library kb doctor                        # health report for manifest/DB/FTS
python -m library kb smoke --query "смысл"         # retrieval smoke check
python -m library kb query --query "смысл"         # query chunks and taxonomy
python -m library kb query-v3 --theme "meaning"    # structured v3 query
python -m library kb extract                       # extract KB candidates
python -m library kb normalize                     # normalize candidates
python -m library kb evidence                      # write evidence rows
python -m library kb extract-quotes                # extract quotes
python -m library kb normalize-quotes              # normalize quotes
python -m library kb load-quotes                   # load quotes into DB
python -m library kb migrate-v3                    # run v3 migration
python -m library kb seed-v3                       # seed v3 data
python -m library kb seed-all                      # seed all data layers
python -m library kb import-concepts               # import concepts from JSON
```

## Schema
### Corpus
- `documents`, `document_chunks`, `document_chunks_fts`

### Distilled knowledge
- `themes`, `principles`, `patterns`, `intervention_styles`, `quotes`

### Cases & evidence
- `cases`, `theme_evidence`, `principle_evidence`, `pattern_evidence`
- `argument_frames`, `relationship_patterns`, `developmental_problems`
- `symbolic_motifs`, `intervention_examples`

### Runtime support
- `source_route_strength`, `bridge_to_action_templates`, `next_step_library`
- `route_quote_packs`, `confidence_tags`, `archetype_interventions`
- `archetype_anti_patterns`, `chunk_embeddings`

## Typical workflow
1. Add PDF/text source to library
2. Extract text into `texts/`
3. Register/update `manifest.json`
4. Run `python -m library kb build`
5. Query with `python -m library kb query --query "..."`

## Semi-automatic ingestion
New PDFs can be dropped into `incoming/`, then:
```bash
python -m library ingest auto
```
