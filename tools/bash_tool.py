"""Bash execution tool for the local AI coding agent."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def bash_run(command: str, timeout: int = 120) -> dict:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            'exit_code': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        logger.error('Bash command timed out: %s', command)
        return {'exit_code': -1, 'stdout': '', 'stderr': f'Timeout after {timeout}s'}
    except Exception as exc:
        logger.error('Bash command failed: %s', exc)
        return {'exit_code': -1, 'stdout': '', 'stderr': str(exc)}
