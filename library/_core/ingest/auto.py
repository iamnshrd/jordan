import subprocess

from library.config import INCOMING, BOOKS, ARTICLES, TEXTS, ROOT, INGEST_REPORT
from library.utils import slugify, save_json
from library._core.ingest.book import register as register_book
from library._core.kb.build import build as build_kb
from library._core.kb.extract import extract as extract_candidates
from library._core.kb.normalize import normalize as normalize_candidates
from library._core.kb.evidence import write_evidence
from library._core.kb.quotes import extract_quotes, normalize_quotes, load_quotes


def classify_target(path):
    name = path.stem.lower()
    if any(x in name for x in ['article', 'essay', 'interview']):
        return ARTICLES
    return BOOKS


def ingest():
    """Process all PDFs in incoming/. Returns report dict."""
    processed, skipped, errors = [], [], []
    for path in sorted(INCOMING.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() != '.pdf':
            skipped.append({'file': path.name, 'reason': 'unsupported_suffix'})
            continue
        target_dir = classify_target(path)
        target_name = slugify(path.stem) + '.pdf'
        target = target_dir / target_name
        if target.exists():
            skipped.append({'file': path.name, 'reason': 'already_exists'})
            path.unlink()
            continue
        path.rename(target)
        text_name = target.stem + '.txt'
        text_path = TEXTS / text_name
        try:
            subprocess.check_call(['pdftotext', str(target), str(text_path)])
            register_book(target.name, text_name, 'text_extracted')
            processed.append({'pdf': str(target.relative_to(ROOT)), 'text': str(text_path.relative_to(ROOT))})
        except (subprocess.CalledProcessError, SystemExit) as e:
            errors.append({'file': str(target.relative_to(ROOT)), 'error': str(e)})
    if processed:
        build_kb()
        extract_candidates()
        normalize_candidates()
        write_evidence()
        extract_quotes()
        normalize_quotes()
        load_quotes()
    report = {'processed': processed, 'skipped': skipped, 'errors': errors}
    save_json(INGEST_REPORT, report)
    return report
