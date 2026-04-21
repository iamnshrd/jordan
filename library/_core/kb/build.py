#!/usr/bin/env python3
"""Knowledge-base builder: ingest manifest documents, chunk text, seed taxonomy."""
import logging
import re

from library.config import MANIFEST, ROOT, invalidate_doc_source_hints_cache

log = logging.getLogger('jordan')
from library.db import connect
from library.utils import load_json, save_json


def load_manifest():
    return load_json(MANIFEST, default={'documents': []})


def _detect_heading(line: str) -> str | None:
    """Return heading text if *line* looks like a section heading, else None."""
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith('#'):
        return stripped.lstrip('#').strip() or None
    if len(stripped) >= 5 and stripped == stripped.upper() and stripped[0].isalpha():
        return stripped
    return None


def normalize_source_text(text: str) -> str:
    """Clean raw source text before chunking.

    Handles OCR form feeds, library metadata headers, and subtitle-style
    transcript dumps with numeric indices + timecodes.
    """
    text = text.replace('\ufeff', '').replace('\x0c', '\n')
    text = re.sub(r'\r\n?', '\n', text)
    lines = text.split('\n')

    filtered: list[str] = []
    saw_timecode = False
    for raw in lines:
        line = raw.strip()
        if not line:
            filtered.append('')
            continue
        line = re.sub(r'^>>\s*', '', line)
        line = re.sub(r'^\d{1,4}\s+', '', line)
        line = re.sub(r'^\d{1,3}:\d{2}(?::\d{2})?\s+', '', line)
        line = re.sub(r'\b\d{1,3}:\d{2}(?::\d{2})?\b', ' ', line)
        line = re.sub(r'\s+', ' ', line).strip()
        if not line:
            filtered.append('')
            continue
        if line.startswith(('Источник:', 'Название:', 'Тип:', 'Примечание:')):
            continue
        if re.fullmatch(r'\d+', line):
            continue
        if re.fullmatch(
            r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}',
            line,
        ):
            saw_timecode = True
            filtered.append('')
            continue
        filtered.append(line)

    if not saw_timecode:
        cleaned = '\n'.join(filtered)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in filtered:
        if not line:
            if buffer:
                joined = ' '.join(buffer).strip()
                if joined:
                    paragraphs.append(joined)
                buffer = []
            continue
        buffer.append(line)
        joined = ' '.join(buffer)
        if len(joined) >= 220 or re.search(r'[.!?]["»]?\s*$', joined):
            paragraphs.append(joined.strip())
            buffer = []
    if buffer:
        paragraphs.append(' '.join(buffer).strip())

    cleaned = '\n\n'.join(p for p in paragraphs if p)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def split_chunks(text, max_chars=None, overlap_chars=None):
    """Split *text* into overlapping chunks respecting section boundaries.

    Returns list of dicts: ``{'text': ..., 'section_title': ...}``.
    """
    from library.utils import get_threshold
    if max_chars is None:
        max_chars = get_threshold('chunk_max_chars', 2200)
    if overlap_chars is None:
        overlap_chars = get_threshold('chunk_overlap_chars', 250)
    text = re.sub(r'\r\n?', '\n', text)
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks: list[dict] = []
    current: list[str] = []
    cur_len = 0
    current_section: str | None = None

    def _flush():
        nonlocal current, cur_len
        if current:
            chunks.append({
                'text': '\n\n'.join(current),
                'section_title': current_section,
            })
            current = []
            cur_len = 0

    def _overlap_paras() -> list[str]:
        """Return trailing paragraphs from the last chunk for overlap."""
        if not chunks:
            return []
        last_text = chunks[-1]['text']
        tail = last_text[-overlap_chars:] if len(last_text) > overlap_chars else last_text
        return [p.strip() for p in tail.split('\n\n') if p.strip()][-2:]

    def _hard_split(text: str) -> list[str]:
        """Last-resort split at word boundaries when no sentence delimiters."""
        parts: list[str] = []
        while len(text) > max_chars:
            cut = text.rfind(' ', 0, max_chars)
            if cut <= 0:
                cut = max_chars
            parts.append(text[:cut].rstrip())
            text = text[cut:].lstrip()
        if text:
            parts.append(text)
        return parts

    def _split_long_para(para: str) -> list[str]:
        """Break a paragraph longer than max_chars into sentence-boundary pieces."""
        if len(para) <= max_chars:
            return [para]
        sentences = re.split(r'(?<=[.!?])\s+', para)
        pieces: list[str] = []
        buf: list[str] = []
        buf_len = 0
        for s in sentences:
            if buf_len + len(s) + 1 > max_chars and buf:
                pieces.append(' '.join(buf))
                buf = []
                buf_len = 0
            if len(s) > max_chars:
                if buf:
                    pieces.append(' '.join(buf))
                    buf = []
                    buf_len = 0
                pieces.extend(_hard_split(s))
                continue
            buf.append(s)
            buf_len += len(s) + 1
        if buf:
            pieces.append(' '.join(buf))
        return pieces or [para]

    for p in paras:
        heading = _detect_heading(p.split('\n')[0])
        if heading:
            _flush()
            current_section = heading

        sub_paras = _split_long_para(p)
        for sp in sub_paras:
            if cur_len + len(sp) + 2 > max_chars and current:
                _flush()
                for op in _overlap_paras():
                    current.append(op)
                    cur_len += len(op) + 2
            current.append(sp)
            cur_len += len(sp) + 2

    _flush()
    return chunks


def init_db(conn):
    """Ensure the schema is fully up-to-date via the migration registry."""
    from library.db import ensure_schema
    ensure_schema(conn)


def upsert_document(conn, source_pdf, text_path, status):
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO documents (source_pdf, text_path, status) '
        'VALUES (?, ?, ?) '
        'ON CONFLICT(source_pdf) DO UPDATE SET '
        'text_path = excluded.text_path, '
        'status = excluded.status',
        (source_pdf, text_path, status),
    )
    conn.commit()
    cur.execute('SELECT id FROM documents WHERE source_pdf = ?', (source_pdf,))
    return cur.fetchone()[0]


def _next_revision_number(cur, document_id: int) -> int:
    row = cur.execute(
        'SELECT COALESCE(MAX(revision_number), 0) + 1 '
        'FROM document_revisions WHERE document_id = ?',
        (document_id,),
    ).fetchone()
    return int(row[0] if row and row[0] is not None else 1)


def replace_chunks(conn, document_id, chunks, *, source_text_mtime=None):
    """Create a new active revision with chunks for *document_id* atomically.

    *chunks* may be a list of strings (legacy) or list of dicts with
    ``text`` and ``section_title`` keys (new structured format).
    """
    cur = conn.cursor()
    use_savepoint = conn.in_transaction
    if use_savepoint:
        cur.execute('SAVEPOINT replace_chunks')
    else:
        cur.execute('BEGIN IMMEDIATE')
    try:
        revision_number = _next_revision_number(cur, document_id)
        cur.execute(
            'INSERT INTO document_revisions (document_id, revision_number, source_text_mtime, status) '
            'VALUES (?, ?, ?, ?)',
            (
                document_id,
                revision_number,
                source_text_mtime,
                'building',
            ),
        )
        revision_id = cur.lastrowid
        real_idx = 0
        for idx, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                text = chunk.get('text')
                if not text:
                    log.warning('Chunk %d for doc %d has no text, skipping',
                                idx, document_id)
                    continue
                section = chunk.get('section_title')
            else:
                if not isinstance(chunk, str):
                    log.warning('Chunk %d for doc %d is not str/dict, skipping',
                                idx, document_id)
                    continue
                text = chunk
                section = None
            cur.execute(
                'INSERT INTO document_chunks (document_id, revision_id, chunk_index, content, char_count, section_title) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (document_id, revision_id, real_idx, text, len(text), section),
            )
            real_idx += 1
        cur.execute(
            'UPDATE document_revisions SET status = ? WHERE id = ?',
            ('active', revision_id),
        )
        cur.execute(
            'UPDATE document_revisions SET status = ? '
            'WHERE document_id = ? AND id <> ? AND status = ?',
            ('superseded', document_id, revision_id, 'active'),
        )
        cur.execute(
            'UPDATE documents SET active_revision_id = ? WHERE id = ?',
            (revision_id, document_id),
        )
        cur.execute(
            "INSERT INTO document_chunks_fts(document_chunks_fts) VALUES ('rebuild')"
        )
        if use_savepoint:
            cur.execute('RELEASE SAVEPOINT replace_chunks')
        else:
            conn.commit()
    except Exception:
        if use_savepoint:
            cur.execute('ROLLBACK TO SAVEPOINT replace_chunks')
            cur.execute('RELEASE SAVEPOINT replace_chunks')
        else:
            conn.rollback()
        raise


def seed_taxonomy(conn):
    cur = conn.cursor()
    themes = [
        ('meaning', 'Meaning as orientation against suffering and chaos.'),
        ('responsibility', 'Voluntary responsibility as stabilizing force.'),
        ('order-and-chaos', 'Dynamic tension between structure and uncertainty.'),
        ('truth', 'Truthful speech as moral and psychological discipline.'),
        ('resentment', 'Resentment as consequence of betrayal, weakness, or evasion.'),
        ('suffering', 'Suffering as irreducible fact demanding response.'),
    ]
    principles = [
        ('clean-up-what-is-in-front-of-you', 'Start with local order before abstract world repair.'),
        ('tell-the-truth-or-at-least-dont-lie', 'Truthfulness is foundational to psychological integrity.'),
        ('take-responsibility-before-blame', 'Assume responsibility before indicting the world.'),
    ]
    patterns = [
        ('avoidance-loop', 'Avoidance generates fear, weakness, and further avoidance.'),
        ('resentment-loop', 'Resentment grows when responsibility is refused but grievance is cultivated.'),
        ('aimlessness', 'Lack of aim corrodes motivation and self-respect.'),
    ]
    styles = [
        ('responsibility-first', 'Reframe the problem around burden, agency, and task.'),
        ('symbolic-reframing', 'Use symbolic or archetypal framing to reveal hidden structure.'),
        ('practical-ordering', 'Turn abstractions into immediate concrete ordering actions.'),
    ]
    cases = [
        ('aimless-young-man', 'Intelligent but disorganized young man lacking aim and structure.', 'responsibility-first', 'Can drift into resentment or paralysis if not engaged.'),
        ('resentful-relationship-loop', 'Relationship conflict intensified by unspoken resentment and self-betrayal.', 'responsibility-first', 'Moralizing without self-examination worsens conflict.'),
    ]
    frames = [
        ('order-vs-chaos', 'Frame the problem as the struggle between stabilizing order and destabilizing chaos.'),
        ('truth-vs-self-deception', 'Frame the problem around lying, distortion, and avoidance of reality.'),
    ]
    rel_patterns = [
        ('covert-contract', 'Unspoken expectation followed by bitterness when the other person does not comply.'),
        ('resentment-through-acquiescence', 'Repeated compliance that curdles into hostility.'),
    ]
    dev_problems = [
        ('failed-aim', 'Life disorganization caused by lack of voluntarily chosen aim.'),
        ('avoidance-identity', 'A self-concept built around withdrawal from challenge.'),
    ]
    motifs = [
        ('dragon', 'Chaos or threat that must be voluntarily confronted.'),
        ('burden', 'Meaningful suffering carried voluntarily.'),
    ]
    examples = [
        ('clean-your-room', 'Restore local order before abstract moral grandstanding.'),
        ('tell-the-truth', 'Reduce chaos by refusing deception and distortion.'),
    ]
    for name, desc in themes:
        cur.execute('INSERT OR IGNORE INTO themes (theme_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in principles:
        cur.execute('INSERT OR IGNORE INTO principles (principle_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in patterns:
        cur.execute('INSERT OR IGNORE INTO patterns (pattern_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in styles:
        cur.execute('INSERT OR IGNORE INTO intervention_styles (style_name, description) VALUES (?, ?)', (name, desc))
    for name, desc, style, risk in cases:
        cur.execute('INSERT OR IGNORE INTO cases (case_name, description, intervention_style, risk_note) VALUES (?, ?, ?, ?)', (name, desc, style, risk))
    for name, desc in frames:
        cur.execute('INSERT OR IGNORE INTO argument_frames (frame_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in rel_patterns:
        cur.execute('INSERT OR IGNORE INTO relationship_patterns (pattern_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in dev_problems:
        cur.execute('INSERT OR IGNORE INTO developmental_problems (problem_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in motifs:
        cur.execute('INSERT OR IGNORE INTO symbolic_motifs (motif_name, description) VALUES (?, ?)', (name, desc))
    for name, desc in examples:
        cur.execute('INSERT OR IGNORE INTO intervention_examples (example_name, description) VALUES (?, ?)', (name, desc))
    conn.commit()


def _doc_needs_rebuild(conn, doc_id, text_path) -> bool:
    """Check if a document's chunks are stale by comparing text file mtime."""
    import os
    cur = conn.cursor()
    row = cur.execute(
        'SELECT COUNT(*) FROM document_chunks '
        'WHERE revision_id = (SELECT active_revision_id FROM documents WHERE id = ?)',
        (doc_id,),
    ).fetchone()
    if not row or row[0] == 0:
        return True
    meta_row = cur.execute(
        'SELECT text_mtime, active_revision_id FROM documents WHERE id = ?', (doc_id,),
    ).fetchone()
    try:
        file_mtime = os.path.getmtime(text_path)
    except OSError:
        return True
    if meta_row and meta_row[1] is None:
        return True
    if meta_row and meta_row[0] is not None:
        return file_mtime > meta_row[0]
    return True


def _validate_manifest_docs(manifest):
    """Return validation report for corpus files required by the manifest."""
    report = {
        'indexed_candidates': 0,
        'missing_files': [],
        'invalid_entries': [],
    }
    for doc in manifest.get('documents', []):
        if not isinstance(doc, dict):
            report['invalid_entries'].append({
                'reason': 'entry-not-dict',
                'entry': doc,
            })
            continue
        if doc.get('status') not in {'text_extracted', 'chunked'}:
            continue
        report['indexed_candidates'] += 1
        if not doc.get('text_path') or not doc.get('source_pdf'):
            report['invalid_entries'].append({
                'reason': 'missing-text-path-or-source-pdf',
                'entry': doc,
            })
            continue
        text_path = ROOT / doc['text_path']
        if not text_path.exists():
            report['missing_files'].append({
                'source_pdf': doc.get('source_pdf', ''),
                'text_path': doc.get('text_path', ''),
            })
    return report


def _raise_manifest_validation_error(report):
    details = []
    if report['missing_files']:
        details.append(
            'missing files: ' + ', '.join(
                item['text_path'] for item in report['missing_files']
            )
        )
    if report['invalid_entries']:
        details.append(f"invalid entries: {len(report['invalid_entries'])}")
    summary = '; '.join(details) if details else 'manifest validation failed'
    raise FileNotFoundError(
        'KB build aborted because corpus files are missing or invalid; '
        + summary
    )


def _run_enrichment_pipeline():
    """Populate derived KB layers after raw chunk build."""
    from library._core.kb.concepts import (
        import_article_concepts, import_beyond_order, import_maps_of_meaning,
        import_twelve_rules,
    )
    from library._core.kb.knowledge import (
        build_chapter_summaries,
        import_canonical_concepts,
        import_structured_knowledge,
    )
    from library._core.kb.extract import extract
    from library._core.kb.normalize import normalize
    from library._core.kb.evidence import write_evidence
    from library._core.kb.quotes import extract_quotes, normalize_quotes, load_quotes
    from library._core.kb.seed import (
        seed_v3, seed_v3_links, seed_v3_motifs, seed_v3_quality,
        seed_v3_runtime_links, seed_v3_steps, seed_quote_pack_items,
    )
    from library._core.kb.voice_patterns import (
        load_voice_patterns,
        summarize_voice_patterns,
    )

    return {
        'canonical_concepts': import_canonical_concepts(),
        'structured_knowledge': import_structured_knowledge(),
        'extract': extract(),
        'normalize': normalize(),
        'evidence': write_evidence(),
        'quotes_extract': extract_quotes(),
        'quotes_normalize': normalize_quotes(),
        'quotes_load': load_quotes(),
        'voice_patterns': load_voice_patterns(),
        'voice_pattern_summary': summarize_voice_patterns(limit=6),
        'concepts': {
            'beyond_order': import_beyond_order(),
            'maps_of_meaning': import_maps_of_meaning(),
            'twelve_rules': import_twelve_rules(),
            'articles': import_article_concepts(),
        },
        'chapter_summaries': build_chapter_summaries(),
        'seed_v3': seed_v3(),
        'seed_v3_links': seed_v3_links(),
        'seed_v3_motifs': seed_v3_motifs(),
        'seed_v3_quality': seed_v3_quality(),
        'seed_v3_runtime_links': seed_v3_runtime_links(),
        'seed_v3_steps': seed_v3_steps(),
        'seed_quote_pack_items': seed_quote_pack_items(),
    }


def prune_superseded_revisions(keep_latest_per_document: int = 0):
    """Delete stale superseded revisions and their orphanable rows.

    By default, all superseded revisions are removed. Set
    ``keep_latest_per_document`` to retain the newest N superseded revisions
    per document for audit/history purposes.
    """
    keep_latest_per_document = max(0, int(keep_latest_per_document))
    with connect() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            'SELECT id, document_id, revision_number '
            'FROM document_revisions '
            "WHERE status = 'superseded' "
            'ORDER BY document_id ASC, revision_number DESC'
        ).fetchall()
        to_delete: list[int] = []
        seen_per_doc: dict[int, int] = {}
        for revision_id, document_id, _revision_number in rows:
            seen = seen_per_doc.get(document_id, 0)
            if seen < keep_latest_per_document:
                seen_per_doc[document_id] = seen + 1
                continue
            to_delete.append(revision_id)

        if not to_delete:
            return {
                'deleted_revisions': 0,
                'deleted_chunks': 0,
                'deleted_quotes': 0,
                'deleted_theme_evidence': 0,
                'deleted_principle_evidence': 0,
                'deleted_pattern_evidence': 0,
                'deleted_embeddings': 0,
                'kept_superseded_per_document': keep_latest_per_document,
            }

        placeholders = ','.join('?' for _ in to_delete)
        chunk_rows = cur.execute(
            f'SELECT id FROM document_chunks WHERE revision_id IN ({placeholders})',
            to_delete,
        ).fetchall()
        chunk_ids = [row[0] for row in chunk_rows]
        deleted_quotes = 0
        deleted_theme_evidence = 0
        deleted_principle_evidence = 0
        deleted_pattern_evidence = 0
        deleted_embeddings = 0

        cur.execute('BEGIN IMMEDIATE')
        try:
            if chunk_ids:
                chunk_placeholders = ','.join('?' for _ in chunk_ids)
                quote_ids = [
                    row[0] for row in cur.execute(
                        f'SELECT id FROM quotes WHERE chunk_id IN ({chunk_placeholders})',
                        chunk_ids,
                    ).fetchall()
                ]
                if quote_ids:
                    quote_placeholders = ','.join('?' for _ in quote_ids)
                    cur.execute(
                        f'DELETE FROM quote_pack_items WHERE quote_id IN ({quote_placeholders})',
                        quote_ids,
                    )
                    deleted_quotes = cur.execute(
                        f'DELETE FROM quotes WHERE id IN ({quote_placeholders})',
                        quote_ids,
                    ).rowcount
                deleted_theme_evidence = cur.execute(
                    f'DELETE FROM theme_evidence WHERE chunk_id IN ({chunk_placeholders})',
                    chunk_ids,
                ).rowcount
                deleted_principle_evidence = cur.execute(
                    f'DELETE FROM principle_evidence WHERE chunk_id IN ({chunk_placeholders})',
                    chunk_ids,
                ).rowcount
                deleted_pattern_evidence = cur.execute(
                    f'DELETE FROM pattern_evidence WHERE chunk_id IN ({chunk_placeholders})',
                    chunk_ids,
                ).rowcount
                deleted_embeddings = cur.execute(
                    f'DELETE FROM chunk_embeddings WHERE chunk_id IN ({chunk_placeholders})',
                    chunk_ids,
                ).rowcount
                deleted_chunks = cur.execute(
                    f'DELETE FROM document_chunks WHERE revision_id IN ({placeholders})',
                    to_delete,
                ).rowcount
            else:
                deleted_chunks = 0

            deleted_revisions = cur.execute(
                f'DELETE FROM document_revisions WHERE id IN ({placeholders})',
                to_delete,
            ).rowcount
            cur.execute("INSERT INTO document_chunks_fts(document_chunks_fts) VALUES ('rebuild')")
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        'deleted_revisions': deleted_revisions,
        'deleted_chunks': deleted_chunks,
        'deleted_quotes': deleted_quotes,
        'deleted_theme_evidence': deleted_theme_evidence,
        'deleted_principle_evidence': deleted_principle_evidence,
        'deleted_pattern_evidence': deleted_pattern_evidence,
        'deleted_embeddings': deleted_embeddings,
        'kept_superseded_per_document': keep_latest_per_document,
    }


def build(force: bool = False, allow_partial: bool = False,
          enrich: bool = True):
    """Main build entry point.

    When *force* is False (default), only documents whose text file is newer
    than the last indexed mtime are re-chunked (incremental build).
    """
    import os
    manifest = load_manifest()
    report = _validate_manifest_docs(manifest)
    if (report['missing_files'] or report['invalid_entries']) and not allow_partial:
        _raise_manifest_validation_error(report)

    with connect() as conn:
        init_db(conn)
        seed_taxonomy(conn)
        indexed_docs = 0
        for doc in manifest.get('documents', []):
            if not isinstance(doc, dict):
                continue
            if doc.get('status') not in {'text_extracted', 'chunked'}:
                continue
            if not doc.get('text_path') or not doc.get('source_pdf'):
                log.warning('Manifest entry missing text_path or source_pdf, skipping: %s', doc)
                continue
            text_path = ROOT / doc['text_path']
            if not text_path.exists():
                log.warning('Manifest text_path is missing, skipping: %s', text_path)
                continue
            doc_id = upsert_document(conn, doc['source_pdf'], doc['text_path'], 'chunked')
            if not force and not _doc_needs_rebuild(conn, doc_id, text_path):
                doc['status'] = 'chunked'
                indexed_docs += 1
                continue
            try:
                text = text_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                log.warning('UTF-8 decode failed for %s, falling back to replace mode', text_path)
                text = text_path.read_text(encoding='utf-8', errors='replace')
            text = normalize_source_text(text)
            chunks = split_chunks(text)
            try:
                mtime = os.path.getmtime(text_path)
            except OSError as exc:
                mtime = None
                log.warning('Could not record mtime for doc %s: %s', doc_id, exc)
            replace_chunks(conn, doc_id, chunks, source_text_mtime=mtime)
            if mtime is not None:
                conn.cursor().execute(
                    'UPDATE documents SET text_mtime = ? WHERE id = ?',
                    (mtime, doc_id),
                )
                conn.commit()
            doc['status'] = 'chunked'
            indexed_docs += 1
        save_json(MANIFEST, manifest)
        invalidate_doc_source_hints_cache()
        cur = conn.cursor()
        counts = {
            'documents': cur.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
            'chunks': cur.execute('SELECT COUNT(*) FROM document_chunks').fetchone()[0],
            'active_chunks': cur.execute(
                'SELECT COUNT(*) FROM document_chunks dc '
                'JOIN documents d ON d.id = dc.document_id '
                'WHERE dc.revision_id = d.active_revision_id'
            ).fetchone()[0],
            'document_revisions': cur.execute(
                'SELECT COUNT(*) FROM document_revisions'
            ).fetchone()[0],
            'indexed_docs': indexed_docs,
            'missing_files': report['missing_files'],
            'invalid_entries': report['invalid_entries'],
            'themes': cur.execute('SELECT COUNT(*) FROM themes').fetchone()[0],
            'principles': cur.execute('SELECT COUNT(*) FROM principles').fetchone()[0],
            'patterns': cur.execute('SELECT COUNT(*) FROM patterns').fetchone()[0],
            'intervention_styles': cur.execute('SELECT COUNT(*) FROM intervention_styles').fetchone()[0],
            'cases': cur.execute('SELECT COUNT(*) FROM cases').fetchone()[0],
            'argument_frames': cur.execute('SELECT COUNT(*) FROM argument_frames').fetchone()[0],
            'relationship_patterns': cur.execute('SELECT COUNT(*) FROM relationship_patterns').fetchone()[0],
            'developmental_problems': cur.execute('SELECT COUNT(*) FROM developmental_problems').fetchone()[0],
            'symbolic_motifs': cur.execute('SELECT COUNT(*) FROM symbolic_motifs').fetchone()[0],
            'intervention_examples': cur.execute('SELECT COUNT(*) FROM intervention_examples').fetchone()[0],
        }
    if enrich:
        enrichment = _run_enrichment_pipeline()
        with connect() as conn:
            cur = conn.cursor()
            counts.update({
                'quotes': cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0],
                'theme_evidence': cur.execute('SELECT COUNT(*) FROM theme_evidence').fetchone()[0],
                'principle_evidence': cur.execute('SELECT COUNT(*) FROM principle_evidence').fetchone()[0],
                'pattern_evidence': cur.execute('SELECT COUNT(*) FROM pattern_evidence').fetchone()[0],
                'bridges': cur.execute('SELECT COUNT(*) FROM bridge_to_action_templates').fetchone()[0],
                'next_steps': cur.execute('SELECT COUNT(*) FROM next_step_library').fetchone()[0],
                'quote_packs': cur.execute('SELECT COUNT(*) FROM route_quote_packs').fetchone()[0],
                'quote_pack_items': cur.execute('SELECT COUNT(*) FROM quote_pack_items').fetchone()[0],
                'canonical_concepts': cur.execute(
                    'SELECT COUNT(*) FROM canonical_concepts'
                ).fetchone()[0],
                'definitions': cur.execute(
                    'SELECT COUNT(*) FROM definitions'
                ).fetchone()[0],
                'claims': cur.execute(
                    'SELECT COUNT(*) FROM claims'
                ).fetchone()[0],
                'practices': cur.execute(
                    'SELECT COUNT(*) FROM practices'
                ).fetchone()[0],
                'voice_patterns': cur.execute(
                    'SELECT COUNT(*) FROM voice_patterns'
                ).fetchone()[0],
                'objections': cur.execute(
                    'SELECT COUNT(*) FROM objections'
                ).fetchone()[0],
                'chapter_summaries': cur.execute(
                    'SELECT COUNT(*) FROM chapter_summaries'
                ).fetchone()[0],
                'cases': cur.execute('SELECT COUNT(*) FROM cases').fetchone()[0],
                'intervention_examples': cur.execute(
                    'SELECT COUNT(*) FROM intervention_examples'
                ).fetchone()[0],
            })
        counts['enrichment'] = enrichment
    return counts
