"""Configuration loader for the local AI coding agent."""

from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / 'config' / 'model.yaml'


def _default_config():
    return {
        'model': {
            'name': 'gemma3:4b',
            'provider': 'ollama',
            'host': 'localhost',
            'port': 11434,
            'base_url': 'http://localhost:11434',
        },
        'run': {
            'max_iterations': 50,
            'temperature': 0.2,
            'timeout': 120,
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/agent.log',
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
