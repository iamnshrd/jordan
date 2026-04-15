#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._core.mentor.tick import tick

TARGET_TELEGRAM = os.environ.get('JORDAN_MENTOR_TARGET_TELEGRAM', '77571089').strip()


def main() -> None:
    result = tick(send=True)
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

    msg = (result.get('rendered_message') or '').strip()
    if result.get('should_send') and msg:
        subprocess.run([
            'openclaw', '--profile', 'jordan-peterson', 'message', 'send',
            '--channel', 'telegram',
            '--target', TARGET_TELEGRAM,
            '--message', msg,
        ], check=True)
        compact['delivered'] = True
        compact['delivery_target'] = TARGET_TELEGRAM
    else:
        compact['delivered'] = False

    print(json.dumps(compact, ensure_ascii=False))


if __name__ == '__main__':
    main()
