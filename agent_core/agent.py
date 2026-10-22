"""Agent loop: think -> tool -> observe -> repeat."""

from __future__ import annotations

import logging

from . import config as agent_config
from .llm import LLMClient

from tools.tool import Tool

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
        # Normalisasi nilai tools agar selalu berupa instance Tool
        normalized = {}
        for key, value in self.tools.items():
            if isinstance(value, Tool):
                normalized[key] = value
            elif isinstance(value, dict) and 'func' in value:
                normalized[key] = Tool(
                    name=value.get('name', key),
                    description=value.get('description', ''),
                    func=value['func'],
                )
            elif callable(value):
                normalized[key] = Tool(name=key, description='', func=value)
            else:
                normalized[key] = value
        self.tools = normalized
        self.max_iterations = max_iterations
        self.history = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        base = (
            'Anda adalah AI coding agent yang membantu developer menulis, '
            'memperbaiki, dan memeriksa kode secara interaktif. Anda dapat '
            'menggunakan tool untuk membaca file, menulis/ketemukan, mengeksekusi '
            'perintah shell, dan mencari di repositori.' + chr(10) + chr(10) +
            'Gunakan tool sesuai kebutuhan. Jawab dalam bahasa sesuai permintaan user.'
        )
        tools_prompt = self._build_tools_prompt()
        tool_invoke = (
            chr(10) + chr(10) +
            'Untuk memanggil tool, tulis dalam format berikut (tanpa markdown code block):' + chr(10) +
            'TOOL: nama_tool' + chr(10) +
            'ARGS: {"arg1": "nilai1"}' + chr(10) +
            'Jika tool membutuhkan konten teks (misalnya write_file), tulis:' + chr(10) +
            'CONTENT:' + chr(10) +
            '<isi teks konten di sini, boleh multiline>' + chr(10) +
            'Setelah tool dieksekusi, Anda akan menerima hasilnya dan dapat melanjutkan.'
        )
        return base + chr(10) + chr(10) + tools_prompt + tool_invoke

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
            logger.debug('Tool %s args=%s result=%s', name, args, result)
            observations.append('Tool: ' + name + ' => ' + str(result))
        return chr(10).join(observations)

    def _parse_text_tool_calls(self, content: str) -> list[object]:
        """Parsing TOOL: / ARGS: / CONTENT: dari teks respons model (fallback untuk
        model yang tidak mendukung native tool calling via Ollama).

        Format yang diharapkan:
            TOOL: nama_tool
            ARGS: {"key": "value"}
            CONTENT:
            <teks konten bebas, boleh multiline, sampai TOOL berikutnya atau EOF>
        """
        import re
        import json

        tool_calls = []

        # Temukan semua posisi 'TOOL: nama' untuk mengetahui batas tiap blok
        tool_pattern = re.compile(r'^TOOL:\s*(\S+)', re.MULTILINE)
        tool_positions = [(m.start(), m.group(1).strip()) for m in tool_pattern.finditer(content)]

        for idx, (start, name) in enumerate(tool_positions):
            # Akhir blok = awal TOOL berikutnya, atau akhir string
            end = tool_positions[idx + 1][0] if idx + 1 < len(tool_positions) else len(content)
            block = content[start:end]

            # Ekstrak ARGS (satu baris JSON)
            args = {}
            args_m = re.search(r'^ARGS:\s*(\{.*\})\s*$', block, re.MULTILINE)
            if args_m:
                try:
                    args = json.loads(args_m.group(1))
                except Exception:
                    args = {}

            # Ekstrak CONTENT (teks setelah baris 'CONTENT:' sampai akhir blok)
            content_m = re.search(r'^CONTENT:\s*$\n(.*)', block, re.DOTALL | re.MULTILINE)
            if content_m:
                args['content'] = content_m.group(1).rstrip('\n')

            tool_calls.append({'name': name, 'arguments': args})

        return tool_calls

    def _build_tools_prompt(self) -> str:
        lines = ['Terdapat tool berikut yang dapat digunakan:', chr(10)]
        for name, tool in self.tools.items():
            if isinstance(tool, Tool):
                lines.append('Tool: ' + tool.name)
                lines.append('Desc: ' + tool.description)
                lines.append('Args: ' + str(getattr(tool, 'args_schema', {})))
            else:
                lines.append('Tool: ' + name)
                lines.append('Desc: ' + tool.get('description', ''))
                lines.append('Args: ' + str(tool.get('args', {})))
        return chr(10).join(lines)

    def _ollama_tools(self) -> list[dict]:
        tools = []
        for name, tool in self.tools.items():
            if isinstance(tool, Tool):
                tools.append({
                    'type': 'function',
                    'function': {
                        'name': tool.name,
                        'description': tool.description,
                        'parameters': getattr(tool, 'args_schema', {
                            'type': 'object',
                            'properties': {},
                        }),
                    },
                })
        return tools

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
                # Fallback: parsing dari teks respons model
                tool_calls = self._parse_text_tool_calls(response.get('content', ''))
            if not tool_calls:
                return response.get('content', '')
            observations = self._execute_tools(tool_calls)
            logger.info('Tool observations appended. Total history: %d', len(self.history))
            self.history.append({'role': 'observation', 'content': observations})
        return 'Max iterations reached.'
