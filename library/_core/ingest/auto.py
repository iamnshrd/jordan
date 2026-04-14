"""Automated PDF ingestion with staging, per-file error isolation, and idempotency.

Pipeline: incoming/ -> processing/ -> processed/ | failed/
Each file gets a manifest entry in ingest_jobs.jsonl.
"""
from __future__ import annotations

import logging
import subprocess
import shutil

from library.config import INCOMING, BOOKS, ARTICLES, TEXTS, ROOT, INGEST_REPORT
from library.utils import slugify, save_json, now_iso, load_json
from library._core.ingest.book import register as register_book
from library._core.kb.build import build as build_kb
from library._core.kb.extract import extract as extract_candidates
from library._core.kb.normalize import normalize as normalize_candidates
from library._core.kb.evidence import write_evidence
from library._core.kb.quotes import extract_quotes, normalize_quotes, load_quotes
from library._core.ingest.epub import convert as epub_convert

log = logging.getLogger('jordan')

PROCESSING = INCOMING.parent / 'processing'
PROCESSED = INCOMING.parent / 'processed'
FAILED = INCOMING.parent / 'failed'
INGEST_JOBS = INCOMING.parent / 'ingest_jobs.jsonl'


def _ensure_dirs():
    for d in (INCOMING, PROCESSING, PROCESSED, FAILED):
        d.mkdir(parents=True, exist_ok=True)


def _append_job(entry: dict):
    """Append a job record to the JSONL manifest."""
    import json
    with open(INGEST_JOBS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _load_processed_set() -> set[str]:
    """Return set of filenames already successfully ingested."""
    import json
    names: set[str] = set()
    if not INGEST_JOBS.exists():
        return names
    for line in INGEST_JOBS.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            log.warning('Skipping malformed line in ingest_jobs.jsonl: %s', line[:120])
            continue
        if rec.get('status') == 'processed':
            names.add(rec.get('file', ''))
    return names


def check_pdftotext() -> bool:
    """Verify pdftotext is available.  Returns True if OK."""
    try:
        subprocess.run(
            ['pdftotext', '-v'],
            capture_output=True,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


def classify_target(path):
    name = path.stem.lower()
    if any(x in name for x in ['article', 'essay', 'interview']):
        return ARTICLES
    return BOOKS


def ingest(dry_run: bool = False):
    """Process all PDFs in incoming/.

    With *dry_run=True* files are scanned but not moved or processed.
    Returns report dict.
    """
    _ensure_dirs()

    has_pdfs = any(
        p.suffix.lower() == '.pdf' for p in INCOMING.iterdir() if p.is_file()
    )
    if has_pdfs and not check_pdftotext():
        msg = ('pdftotext not found. Install poppler-utils '
               '(apt install poppler-utils / brew install poppler).')
        log.error(msg)
        return {'error': msg, 'processed': [], 'skipped': [], 'errors': []}

    already_done = _load_processed_set()

    processed, skipped, errors = [], [], []
    need_rebuild = False

    supported_suffixes = {'.pdf', '.epub'}
    for path in sorted(INCOMING.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_suffixes:
            skipped.append({'file': path.name, 'reason': 'unsupported_suffix'})
            continue

        if path.name in already_done:
            skipped.append({'file': path.name, 'reason': 'already_ingested'})
            continue

        if dry_run:
            processed.append({'file': path.name, 'dry_run': True})
            continue

        staging_path = PROCESSING / path.name
        try:
            shutil.move(str(path), str(staging_path))
        except OSError as exc:
            errors.append({'file': path.name, 'error': f'move_to_processing: {exc}'})
            _append_job({'file': path.name, 'status': 'error',
                         'error': str(exc), 'timestamp': now_iso()})
            continue

        target_dir = classify_target(staging_path)
        base_name = slugify(staging_path.stem)
        suffix = staging_path.suffix.lower()
        target_name = base_name + suffix
        target = target_dir / target_name

        if target.exists():
            import hashlib as _hl
            h = _hl.md5(staging_path.read_bytes()).hexdigest()[:8]
            alt_name = f'{base_name}_{h}{suffix}'
            alt_target = target_dir / alt_name
            if alt_target.exists():
                skipped.append({'file': path.name, 'reason': 'already_exists'})
                shutil.move(str(staging_path), str(PROCESSED / path.name))
                _append_job({'file': path.name, 'status': 'skipped_duplicate',
                             'timestamp': now_iso()})
                continue
            target_name = alt_name
            target = alt_target

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging_path), str(target))

            text_name = target.stem + '.txt'
            text_path = TEXTS / text_name
            TEXTS.mkdir(parents=True, exist_ok=True)

            if target.suffix.lower() == '.epub':
                import zipfile, tempfile
                from pathlib import Path as _P
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = _P(tmp).resolve()
                    with zipfile.ZipFile(str(target), 'r') as zf:
                        safe = []
                        for member in zf.namelist():
                            dest = (tmp_path / member).resolve()
                            if not str(dest).startswith(str(tmp_path)):
                                log.warning('Skipping suspicious zip entry: %s', member)
                                continue
                            safe.append(member)
                        zf.extractall(tmp, members=safe)
                    epub_convert(tmp, str(text_path))
            else:
                subprocess.check_call(['pdftotext', str(target), str(text_path)])
            register_book(target.name, text_name, 'text_extracted')

            shutil.copy2(str(target), str(PROCESSED / path.name))
            _append_job({
                'file': path.name,
                'status': 'processed',
                'pdf': str(target.relative_to(ROOT)),
                'text': str(text_path.relative_to(ROOT)),
                'timestamp': now_iso(),
            })
            processed.append({
                'pdf': str(target.relative_to(ROOT)),
                'text': str(text_path.relative_to(ROOT)),
            })
            need_rebuild = True

        except Exception as exc:
            log.exception('Ingest failed for %s', path.name)
            fail_dest = FAILED / path.name
            for src in (target, staging_path):
                if src.exists():
                    try:
                        shutil.move(str(src), str(fail_dest))
                    except OSError:
                        pass
                    break
            errors.append({'file': path.name, 'error': str(exc)})
            _append_job({'file': path.name, 'status': 'error',
                         'error': str(exc), 'timestamp': now_iso()})

    if need_rebuild and not dry_run:
        build_kb()
        extract_candidates()
        normalize_candidates()
        write_evidence()
        extract_quotes()
        normalize_quotes()
        load_quotes()
        try:
            from library._core.kb.embeddings import embed_all_chunks, get_embedding_provider
            provider = get_embedding_provider()
            if provider is not None:
                result = embed_all_chunks(provider)
                log.info('Embeddings generated: %s', result)
            else:
                log.info('No embedding provider configured, skipping embedding generation')
        except Exception as exc:
            log.warning('Embedding generation skipped: %s', exc)

    report = {
        'processed': processed,
        'skipped': skipped,
        'errors': errors,
        'dry_run': dry_run,
    }
    save_json(INGEST_REPORT, report)
    return report
