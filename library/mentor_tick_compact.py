#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library._core.mentor.tick import tick


def main() -> None:
    result = tick()
    event = result.get('selected_event') or {}
    compact = {
        'route': result.get('route'),
        'skip': result.get('skip'),
        'skip_reason': result.get('skip_reason'),
        'event_type': event.get('type'),
        'event_summary': event.get('summary'),
        'should_send': result.get('should_send'),
        'sent': result.get('sent'),
    }
    print(json.dumps(compact, ensure_ascii=False))


if __name__ == '__main__':
    main()
