"""File read / write / glob tools."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(path: str, limit: int = 20000) -> dict:
    p = Path(path)
    try:
        if not p.exists():
            return {'status': 'error', 'message': 'File not found: ' + path}
        if not p.is_file():
            return {'status': 'error', 'message': 'Path is not a file: ' + path}
        content = p.read_text(encoding='utf-8')
        return {'status': 'success', 'content': content[:limit]}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}

def write_file(path: str, content: str) -> dict:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return {'status': 'success', 'message': 'Wrote ' + path}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}


def glob_files(pattern: str) -> dict:
    try:
        matches = sorted(Path('.').glob(pattern))
        return {'status': 'success', 'files': [str(p) for p in matches]}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}
