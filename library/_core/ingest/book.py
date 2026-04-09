from library.config import BOOKS, TEXTS, MANIFEST
from library.utils import load_json, save_json


def register(pdf_name, text_name=None, status='pending_text_extraction'):
    """Register a book PDF in manifest.json. Returns the entry dict."""
    manifest = load_json(MANIFEST, {'documents': []})
    pdf = BOOKS / pdf_name
    if not pdf.exists():
        raise SystemExit(f'Book not found: {pdf}')
    TEXTS.mkdir(parents=True, exist_ok=True)
    rel_text = f'texts/{text_name}' if text_name else None
    for entry in manifest['documents']:
        if entry.get('source_pdf') == str(pdf.relative_to(MANIFEST.parent)):
            entry['text_path'] = rel_text
            entry['status'] = status
            save_json(MANIFEST, manifest)
            return entry
    entry = {
        'source_pdf': str(pdf.relative_to(MANIFEST.parent)),
        'text_path': rel_text,
        'status': status,
    }
    manifest['documents'].append(entry)
    save_json(MANIFEST, manifest)
    return entry
