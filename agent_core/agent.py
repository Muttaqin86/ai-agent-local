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
            'menggunakan tool untuk membaca file, menulis/menemukan, mengeksekusi '
            'perintah shell, dan mencari di repositori.' + chr(10) + chr(10) +
            'PENTING: Sebelum mengedit file yang SUDAH ADA, selalu baca terlebih dahulu '
            'file tersebut dengan read_file untuk mengetahui isinya saat ini. Jangan '
            'menebak isi file; gunakan teks yang EXAKT dari hasil read_file sebagai '
            'old_str dalam edit_file.' + chr(10) +
            'Gunakan edit_file untuk mengubah sebagian isi file (misalnya menambah, '
            'mengganti, atau menghapus teks tertentu). Jangan gunakan write_file untuk '
            'memodifikasi file yang sudah ada, karena write_file akan MENGHAPUS dan '
            'mengganti SELURUH isi file dengan konten baru. Gunakan write_file hanya '
            'untuk membuat file BARU atau jika sengaja ingin menimpa seluruh isi file.' + chr(10) + chr(10) +
            'SETELAH edit_file atau write_file dieksekusi, SELALU verifikasi dengan '
            'memanggil read_file kembali pada path yang sama dan bandingkan isi baru '
            'dengan yang diharapkan. Jika hasil read_file belum sesuai, perbaiki dengan '
            'edit_file lagi. Jangan bilang "selesai" sebelum Anda memverifikasi isi file '
            'secara langsung.' + chr(10) + chr(10) +
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

        Format yang diharapkan (baru):
            TOOL: nama_tool
            ARGS: {"key": "value"}
            CONTENT:
            <teks konten bebas, boleh multiline, sampai TOOL berikutnya atau EOF>

        Format lama (fallback, konten di dalam ARGS JSON):
            TOOL: nama_tool
            ARGS: {"key": "value", "content": "..."}

        Fallback tanpa TOOL: (hanya CONTENT:):
            CONTENT:
            <teks konten>
        """
        import re
        import json

        def strip_code_blocks(text: str) -> str:
            """Hapus penanda markdown code block (```lang ... ```) dari teks."""
            text = re.sub(r'^```\w*\s*\n', '', text, flags=re.MULTILINE)
            text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
            return text.strip()

        tool_calls = []

        # Temukan semua posisi 'TOOL: nama' untuk mengetahui batas tiap blok
        tool_pattern = re.compile(r'^TOOL:\s*(\S+)', re.MULTILINE)
        tool_positions = [(m.start(), m.group(1).strip()) for m in tool_pattern.finditer(content)]

        # Jika tidak ada TOOL: tapi ada CONTENT:, buat satu synthetic tool call
        if not tool_positions:
            content_m = re.search(r'^CONTENT:\s*$\n(.*)', content, re.DOTALL | re.MULTILINE)
            if content_m:
                args = {'content': strip_code_blocks(content_m.group(1)).rstrip('\n')}
                if 'path' not in args:
                    args['path'] = 'index.html'
                tool_calls.append({'name': 'write_file', 'arguments': args})
            return tool_calls

        for idx, (start, name) in enumerate(tool_positions):
            # Akhir blok = awal TOOL berikutnya, atau akhir string
            end = tool_positions[idx + 1][0] if idx + 1 < len(tool_positions) else len(content)
            block = content[start:end]

            args = {}

            # --- Format baru: ambil CONTENT dari delimiter CONTENT: ---
            content_m = re.search(r'^CONTENT:\s*$\n(.*)', block, re.DOTALL | re.MULTILINE)
            if content_m:
                args['content'] = strip_code_blocks(content_m.group(1)).rstrip('\n')

            # --- Ambil ARGS (satu baris JSON, boleh multiline jika konten di dalam) ---
            args_m = re.search(r'^ARGS:\s*(\{.*\})\s*$', block, re.MULTILINE | re.DOTALL)
            if args_m:
                try:
                    parsed = json.loads(args_m.group(1))
                    if isinstance(parsed, dict):
                        # Jika sudah ada 'content' dari format baru, jangan timpa
                        for k, v in parsed.items():
                            if k not in args:
                                args[k] = v
                except Exception:
                    # JSON rusak (mis. triple quotes di dalam string). Coba ekstrak
                    # path dan content secara kasar via regex agar tidak sia-sia.
                    path_m = re.search(r'"path"\s*:\s*"([^"]+)"', args_m.group(1))
                    if path_m and 'path' not in args:
                        args['path'] = path_m.group(1)
                    if 'content' not in args:
                        # Coba ambil isi setelah "content": sampai akhir blok
                        c_m = re.search(r'"content"\s*:\s*"{1,3}(.*?)"{1,3}?\s*\}?\s*$',
                                        args_m.group(1), re.DOTALL)
                        if c_m:
                            args['content'] = strip_code_blocks(c_m.group(1)).strip()

            # Default path kalau model lupa sertakan "path"
            if 'path' not in args:
                args['path'] = 'index.html'

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

    def _has_tool_error(self, observations) -> bool:
        """Cek apakah salah satu hasil tool mengandung status error."""
        text = str(observations)
        return ('"status": "error"' in text) or ("'status': 'error'" in text)

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

            # Jika ada tool yang gagal, jangan anggap selesai. Beri tahu LLM
            # agar memperbaiki parameter (misalnya old_str yang tidak cocok).
            if self._has_tool_error(observations):
                logger.warning('Tool error detected; continuing loop for correction')
                continue

            # Setelah edit_file/write_file sukses, paksa verifikasi read_file
            # agar agent memastikan perubahan benar-benar tertulis.
            needs_verify = False
            for tc in tool_calls:
                if tc.get('name') in ('edit_file', 'write_file'):
                    needs_verify = True
                    break
            if needs_verify:
                for tc in tool_calls:
                    if tc.get('name') in ('edit_file', 'write_file'):
                        path = tc.get('arguments', {}).get('path')
                        if path:
                            verify = self.tools.get('read_file')
                            if verify:
                                result = verify({'path': path})
                                self.history.append({
                                    'role': 'observation',
                                    'content': 'VERIFIKASI read_file(' + str(path) + '): ' + str(result),
                                })
                                logger.info('Verification read_file for %s', path)
                continue
        return 'Max iterations reached.'
