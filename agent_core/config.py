"""Configuration loader for the local AI coding agent."""

from pathlib import Path

import os
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / 'config' / 'model.yaml'


def _default_config():
    return {
        'model': {
            'name': os.environ.get('AGENT_MODEL', 'gemma3:4b'),
            'provider': os.environ.get('AGENT_PROVIDER', 'ollama'),
            'api_key': os.environ.get('AGENT_API_KEY', ''),
            'host': os.environ.get('AGENT_HOST', 'localhost'),
            'port': int(os.environ.get('AGENT_PORT', 11434)),
            'base_url': os.environ.get('AGENT_BASE_URL', 'http://localhost:11434'),
        },
        'run': {
            'max_iterations': int(os.environ.get('AGENT_MAX_ITERATIONS', 50)),
            'temperature': float(os.environ.get('AGENT_TEMPERATURE', 0.2)),
            'timeout': int(os.environ.get('AGENT_TIMEOUT', 120)),
        },
        'logging': {
            'level': os.environ.get('AGENT_LOG_LEVEL', 'INFO'),
            'file': os.environ.get('AGENT_LOG_FILE', 'logs/agent.log'),
        },
    }


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    config = _default_config()
    if DEFAULT_CONFIG_PATH.exists():
        try:
            with open(DEFAULT_CONFIG_PATH, 'r') as fh:
                file_config = yaml.safe_load(fh) or {}
        except Exception:
            file_config = {}
        config = _deep_merge(config, file_config)
    return config
