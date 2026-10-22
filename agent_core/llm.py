"""LLM client abstraction for Ollama."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, model_name: str, base_url: str, temperature: float = 0.2):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature

    def complete(self, messages: list[dict[str, str]]) -> dict:
        payload = {
            'model': self.model_name,
            'messages': messages,
            'temperature': self.temperature,
            'stream': False,
        }
        try:
            resp = requests.post(
                self.base_url + '/api/chat',
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data)
        except Exception as exc:
            logger.error('LLM request failed: %s', exc)
            return {'content': '', 'tool_calls': [], 'error': str(exc)}

    def _parse_response(self, data: dict) -> dict:
        message = data.get('message', {})
        content = message.get('content', '')
        tool_calls = []
        for tc in message.get('tool_calls') or []:
            tool_calls.append({
                'name': tc.get('function', {}).get('name'),
                'arguments': tc.get('function', {}).get('arguments'),
            })
        return {'content': content, 'tool_calls': tool_calls}
