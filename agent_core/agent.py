"""Agent loop: think -> tool -> observe -> repeat."""

from __future__ import annotations

import logging

from . import config as agent_config
from .llm import LLMClient

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        model_name=None,
        base_url=None,
        tools=None,
        max_iterations=50,
        temperature=0.2,
    ):
        self.config = agent_config.load_config()
        self.llm = LLMClient(
            model_name=model_name or self.config['model']['name'],
            base_url=base_url or self.config['model']['base_url'],
            temperature=temperature,
        )
        self.tools = tools or {}
        self.max_iterations = max_iterations
        self.history = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return (
            'Anda adalah AI coding agent yang membantu developer menulis, '
            'memperbaiki, dan memeriksa kode secara interaktif. Anda dapat '
            'menggunakan tool untuk membaca file, menulis/ketemukan, mengeksekusi '
            'perintah shell, dan mencari di repositori.' + chr(10) + chr(10) +
            'Gunakan tool sesuai kebutuhan. Jawab dalam bahasa sesuai permintaan user.'
        )

    def _format_tool_calls(self, tool_calls: list[object]) -> str:
        parts = []
        for tc in tool_calls:
            parts.append('Action: ' + str(tc.get('name')))
            parts.append('Arguments: ' + str(tc.get('arguments')))
        return chr(10).join(parts)

    def _format_messages(self) -> list[dict[str, str]]:
        return [{'role': 'system', 'content': self.system_prompt}] + self.history

    def _execute_tools(self, tool_calls: list[object]) -> str:
        observations = []
        for tc in tool_calls:
            name = tc.get('name')
            args = tc.get('arguments', {})
            tool = self.tools.get(name)
            if tool is None:
                observations.append('Tool not found: ' + name)
                continue
            try:
                result = tool(args)
            except Exception as e:
                result = 'Error: ' + str(e)
            observations.append('Tool: ' + name + ' => ' + str(result))
        return chr(10).join(observations)

    def _build_tools_prompt(self) -> str:
        lines = ['Terdapat tool berikut yang dapat digunakan:', chr(10)]
        for name, tool in self.tools.items():
            lines.append('Tool: ' + name)
            lines.append('Desc: ' + tool.get('description', ''))
            lines.append('Args: ' + str(tool.get('args', {})))
        return chr(10).join(lines)

    def run(self, user_input: str) -> str:
        self.history.append({'role': 'user', 'content': user_input})
        for iteration in range(self.max_iterations):
            logger.info('Agent iteration %d', iteration)
            messages = self._format_messages()
            response = self.llm.complete(messages)
            logger.info('LLM response: %s', str(response.get('content', ''))[:200])
            self.history.append({'role': 'assistant', 'content': response.get('content', '')})
            tool_calls = response.get('tool_calls') or []
            if not tool_calls:
                return response.get('content', '')
            observations = self._execute_tools(tool_calls)
            logger.info('Tool observations appended. Total history: %d', len(self.history))
            self.history.append({'role': 'observation', 'content': observations})
        return 'Max iterations reached.'
