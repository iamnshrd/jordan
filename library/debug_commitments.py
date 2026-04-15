#!/usr/bin/env python3
from __future__ import annotations
import sys, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from library._adapters.fs_store import FileSystemStore
from library._core.mentor.commitments import record_commitment, load_commitments, best_open_commitment, maybe_resolve_from_reply

with tempfile.TemporaryDirectory() as td:
    store = FileSystemStore(Path(td))
    a = record_commitment('Я завтра напишу ему и закрою этот разговор', store=store)
    b = record_commitment('Я на этой неделе разберу этот вопрос', store=store)
    print(json.dumps(load_commitments(store=store), ensure_ascii=False, indent=2))
    print('best', json.dumps(best_open_commitment(store=store), ensure_ascii=False, indent=2))
    print('resolve', maybe_resolve_from_reply('Да, я написал ему и закрыл этот разговор', store=store))
    print(json.dumps(load_commitments(store=store), ensure_ascii=False, indent=2))
