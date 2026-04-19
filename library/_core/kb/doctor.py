#!/usr/bin/env python3
"""KB health checks and smoke diagnostics."""
from __future__ import annotations

from pathlib import Path

from library.config import MANIFEST, ROOT
from library.db import connect
from library.utils import load_json, fts_query


def _manifest_report() -> dict:
    manifest = load_json(MANIFEST, default={'documents': []})
    docs = manifest.get('documents', [])
    indexed_candidates = []
    missing_files = []
    invalid_entries = []

    for doc in docs:
        if not isinstance(doc, dict):
            invalid_entries.append({'reason': 'entry-not-dict', 'entry': doc})
            continue
        if doc.get('status') not in {'text_extracted', 'chunked'}:
            continue
        indexed_candidates.append(doc)
        if not doc.get('text_path') or not doc.get('source_pdf'):
            invalid_entries.append({
                'reason': 'missing-text-path-or-source-pdf',
                'entry': doc,
            })
            continue
        text_path = ROOT / doc['text_path']
        if not text_path.exists():
            missing_files.append({
                'source_pdf': doc.get('source_pdf', ''),
                'text_path': doc.get('text_path', ''),
            })

    return {
        'manifest_documents': len(docs),
        'indexed_candidates': len(indexed_candidates),
        'missing_files': missing_files,
        'invalid_entries': invalid_entries,
    }


def doctor() -> dict:
    """Return KB health report with manifest, DB and FTS status."""
    manifest = _manifest_report()
    with connect() as conn:
        cur = conn.cursor()
        counts = {
            'documents': cur.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
            'chunks': cur.execute('SELECT COUNT(*) FROM document_chunks').fetchone()[0],
            'active_chunks': cur.execute(
                'SELECT COUNT(*) FROM document_chunks dc '
                'JOIN documents d ON d.id = dc.document_id '
                'WHERE dc.revision_id = d.active_revision_id'
            ).fetchone()[0],
            'document_revisions': cur.execute('SELECT COUNT(*) FROM document_revisions').fetchone()[0],
            'quotes': cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0],
            'theme_evidence': cur.execute('SELECT COUNT(*) FROM theme_evidence').fetchone()[0],
            'principle_evidence': cur.execute('SELECT COUNT(*) FROM principle_evidence').fetchone()[0],
            'pattern_evidence': cur.execute('SELECT COUNT(*) FROM pattern_evidence').fetchone()[0],
            'canonical_concepts': cur.execute('SELECT COUNT(*) FROM canonical_concepts').fetchone()[0],
            'definitions': cur.execute('SELECT COUNT(*) FROM definitions').fetchone()[0],
            'claims': cur.execute('SELECT COUNT(*) FROM claims').fetchone()[0],
            'practices': cur.execute('SELECT COUNT(*) FROM practices').fetchone()[0],
            'objections': cur.execute('SELECT COUNT(*) FROM objections').fetchone()[0],
            'chapter_summaries': cur.execute('SELECT COUNT(*) FROM chapter_summaries').fetchone()[0],
            'bridges': cur.execute('SELECT COUNT(*) FROM bridge_to_action_templates').fetchone()[0],
            'next_steps': cur.execute('SELECT COUNT(*) FROM next_step_library').fetchone()[0],
        }

        fts_ok = True
        fts_error = ''
        try:
            cur.execute('SELECT COUNT(*) FROM document_chunks_fts').fetchone()
        except Exception as exc:
            fts_ok = False
            fts_error = str(exc)

    issues = []
    if manifest['missing_files']:
        issues.append('manifest-missing-files')
    if manifest['invalid_entries']:
        issues.append('manifest-invalid-entries')
    if counts['documents'] == 0:
        issues.append('db-empty-documents')
    if counts['active_chunks'] == 0:
        issues.append('db-empty-chunks')
    if not fts_ok:
        issues.append('fts-unavailable')

    if not issues:
        status = 'ok'
    elif counts['chunks'] == 0 or not fts_ok:
        status = 'fail'
    else:
        status = 'warn'

    return {
        'status': status,
        'issues': issues,
        'manifest': manifest,
        'counts': counts,
        'fts': {
            'ok': fts_ok,
            'error': fts_error,
        },
    }


def smoke(query: str = 'смысл') -> dict:
    """Run smoke diagnostics against retrieval-critical KB paths."""
    q = fts_query(query, expand_synonyms=False) or query
    health = doctor()
    with connect() as conn:
        cur = conn.cursor()
        fts_hits = []
        fts_error = ''
        try:
            cur.execute(
                """
                SELECT dc.id, dc.chunk_index,
                       snippet(document_chunks_fts, 0, '[', ']', ' … ', 12) AS snippet
                FROM document_chunks_fts fts
                JOIN document_chunks dc ON dc.id = fts.rowid
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.revision_id = d.active_revision_id
                  AND document_chunks_fts MATCH ?
                LIMIT 3
                """,
                (q,),
            )
            fts_hits = [
                {'id': row[0], 'chunk_index': row[1], 'snippet': row[2]}
                for row in cur.fetchall()
            ]
        except Exception as exc:
            fts_error = str(exc)

    issues = list(health['issues'])
    if fts_error:
        issues.append('fts-query-failed')
    elif not fts_hits:
        issues.append('fts-zero-hits')

    status = 'ok' if not issues else ('fail' if 'fts-query-failed' in issues or 'db-empty-chunks' in issues else 'warn')
    return {
        'status': status,
        'issues': issues,
        'query': query,
        'fts_query': q,
        'health': health,
        'fts_hits': fts_hits,
        'fts_error': fts_error,
    }
