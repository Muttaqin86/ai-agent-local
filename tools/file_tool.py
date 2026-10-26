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


def edit_file(path: str, old_str: str, new_str: str, replace_all: bool = False) -> dict:
    """Ganti teks lama (old_str) dengan teks baru (new_str) dalam file.

    Args:
        path: path ke file yang akan diedit.
        old_str: teks yang ingin dicari dan diganti.
        new_str: teks pengganti.
        replace_all: jika True, ganti semua occurrence; jika False, hanya satu occurrence.
    """
    p = Path(path)
    try:
        if not p.exists():
            return {'status': 'error', 'message': 'File not found: ' + path}
        if not p.is_file():
            return {'status': 'error', 'message': 'Path is not a file: ' + path}

        content = p.read_text(encoding='utf-8')

        if old_str not in content:
            return {'status': 'error', 'message': 'old_str not found in file: ' + path}

        count = content.count(old_str)
        if count > 1 and not replace_all:
            return {
                'status': 'error',
                'message': (
                    'old_str appears {} times in file. '
                    'Use replace_all=True to replace all, or make old_str more unique.'
                ).format(count),
            }

        if replace_all:
            new_content = content.replace(old_str, new_str)
            replaced = count
        else:
            new_content = content.replace(old_str, new_str, 1)
            replaced = 1

        p.write_text(new_content, encoding='utf-8')
        return {
            'status': 'success',
            'message': 'Edited {} replacement(s) in {}'.format(replaced, path),
        }
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}
