#!/usr/bin/env python3
"""Rebuild and inspect transcript-derived voice patterns stored in the KB."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from library._core.kb.voice_patterns import (
    load_voice_patterns,
    summarize_voice_patterns,
)


def main() -> None:
    extract_result = load_voice_patterns()
    summary = summarize_voice_patterns(limit=8)
    print(json.dumps(
        {
            'extract': extract_result,
            'summary': summary,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == '__main__':
    main()
