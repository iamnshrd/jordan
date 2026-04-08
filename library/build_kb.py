#!/usr/bin/env python3
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library')
MANIFEST = ROOT / 'manifest.json'
DB = ROOT / 'jordan_knowledge.db'


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'documents': []}


def split_chunks(text, max_chars=2200):
    text = re.sub(r'\r\n?', '\n', text)
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = []
    cur_len = 0
    for p in paras:
        if cur_len + len(p) + 2 > max_chars and current:
            chunks.append('\n\n'.join(current))
            current = [p]
            cur_len = len(p)
        else:
            current.append(p)
            cur_len += len(p) + 2
    if current:
        chunks.append('\n\n'.join(current))
    return chunks


def init_db(conn):
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_pdf TEXT UNIQUE,
      text_path TEXT,
      status TEXT
    );
    CREATE TABLE IF NOT EXISTS document_chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      char_count INTEGER NOT NULL,
      FOREIGN KEY(document_id) REFERENCES documents(id)
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(content, content='document_chunks', content_rowid='id');
    CREATE TABLE IF NOT EXISTS themes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      theme_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS principles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      principle_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS patterns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pattern_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS intervention_styles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      style_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS quotes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER,
      chunk_id INTEGER,
      quote_text TEXT,
      note TEXT,
      quote_type TEXT,
      theme_name TEXT,
      principle_name TEXT,
      pattern_name TEXT,
      FOREIGN KEY(document_id) REFERENCES documents(id),
      FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
    );
    CREATE TABLE IF NOT EXISTS cases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      case_name TEXT UNIQUE,
      description TEXT,
      intervention_style TEXT,
      risk_note TEXT
    );
    CREATE TABLE IF NOT EXISTS argument_frames (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      frame_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS relationship_patterns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pattern_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS developmental_problems (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      problem_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS symbolic_motifs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      motif_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS intervention_examples (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      example_name TEXT UNIQUE,
      description TEXT
    );
    CREATE TABLE IF NOT EXISTS theme_evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      theme_id INTEGER,
      chunk_id INTEGER,
      note TEXT,
      FOREIGN KEY(theme_id) REFERENCES themes(id),
      FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
    );
    CREATE TABLE IF NOT EXISTS principle_evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      principle_id INTEGER,
      chunk_id INTEGER,
      note TEXT,
      FOREIGN KEY(principle_id) REFERENCES principles(id),
      FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
    );
    CREATE TABLE IF NOT EXISTS pattern_evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pattern_id INTEGER,
      chunk_id INTEGER,
      note TEXT,
      FOREIGN KEY(pattern_id) REFERENCES patterns(id),
      FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
    );
    ''')
    conn.commit()


def upsert_document(conn, source_pdf, text_path, status):
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO documents (id, source_pdf, text_path, status) VALUES ((SELECT id FROM documents WHERE source_pdf = ?), ?, ?, ?)', (source_pdf, source_pdf, text_path, status))
    conn.commit()
    cur.execute('SELECT id FROM documents WHERE source_pdf = ?', (source_pdf,))
    return cur.fetchone()[0]


def replace_chunks(conn, document_id, chunks):
    cur = conn.cursor()
    cur.execute('DELETE FROM document_chunks WHERE document_id = ?', (document_id,))
    conn.commit()
    for idx, chunk in enumerate(chunks):
        cur.execute('INSERT INTO document_chunks (document_id, chunk_index, content, char_count) VALUES (?, ?, ?, ?)', (document_id, idx, chunk, len(chunk)))
        rowid = cur.lastrowid
        cur.execute('INSERT INTO document_chunks_fts(rowid, content) VALUES (?, ?)', (rowid, chunk))
    conn.commit()


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


def main():
    manifest = load_manifest()
    conn = sqlite3.connect(DB)
    init_db(conn)
    seed_taxonomy(conn)
    for doc in manifest.get('documents', []):
        if doc.get('status') not in {'text_extracted', 'chunked'}:
            continue
        text_path = ROOT / doc['text_path']
        if not text_path.exists():
            continue
        text = text_path.read_text(errors='ignore')
        chunks = split_chunks(text)
        doc_id = upsert_document(conn, doc['source_pdf'], doc['text_path'], 'chunked')
        replace_chunks(conn, doc_id, chunks)
        doc['status'] = 'chunked'
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    cur = conn.cursor()
    counts = {
        'documents': cur.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
        'chunks': cur.execute('SELECT COUNT(*) FROM document_chunks').fetchone()[0],
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
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
