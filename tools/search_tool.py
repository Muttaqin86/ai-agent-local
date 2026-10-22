"""Code search tool using grep-like scanning."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def search_code(pattern: str, path: str = '.', recurse: bool = True, file_pattern: str = '*.py') -> dict:
    try:
        root = Path(path).resolve()
        flags = re.IGNORECASE
        regex = re.compile(pattern, flags)
        results = []
        for p in root.rglob('*') if recurse else root.glob('*'):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    results.append({'file': str(p), 'line': i, 'text': line.strip()})
                    if len(results) >= 200:
                        break
            if len(results) >= 200:
                break
        return {'status': 'success', 'matches': results}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}
def foo():
    return 2
