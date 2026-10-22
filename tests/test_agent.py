


import unittest
from unittest.mock import patch, MagicMock
# Test minimal for the local AI coding agent.

class TestAgentLoop(unittest.TestCase):
    def test_agent_imports(self):
        from agent_core.agent import Agent
        assert Agent is not None

    def test_parse_text_tool_calls_write_file(self):
        """_parse_text_tool_calls should extract path and content for write_file."""
        from agent_core.agent import Agent
        a = Agent.__new__(Agent)
        content = (
            'TOOL: write_file\n'
            'ARGS: {"path": "out.txt"}\n'
            'CONTENT:\n'
            'line one\n'
            'line two\n'
        )
        calls = a._parse_text_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['name'], 'write_file')
        self.assertEqual(calls[0]['arguments']['path'], 'out.txt')
        self.assertEqual(calls[0]['arguments']['content'], 'line one\nline two')

    def test_parse_text_tool_calls_read_file(self):
        """_parse_text_tool_calls should extract path for read_file (no CONTENT)."""
        from agent_core.agent import Agent
        a = Agent.__new__(Agent)
        content = (
            'TOOL: read_file\n'
            'ARGS: {"path": "in.txt"}\n'
        )
        calls = a._parse_text_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['name'], 'read_file')
        self.assertEqual(calls[0]['arguments']['path'], 'in.txt')

    def test_parse_text_tool_calls_multiple(self):
        """Multiple TOOL blocks should each be parsed independently."""
        from agent_core.agent import Agent
        a = Agent.__new__(Agent)
        content = (
            'TOOL: write_file\n'
            'ARGS: {"path": "a.txt"}\n'
            'CONTENT:\n'
            'hello\n'
            'TOOL: read_file\n'
            'ARGS: {"path": "b.txt"}\n'
        )
        calls = a._parse_text_tool_calls(content)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['name'], 'write_file')
        self.assertEqual(calls[0]['arguments']['path'], 'a.txt')
        self.assertEqual(calls[0]['arguments']['content'], 'hello')
        self.assertEqual(calls[1]['name'], 'read_file')
        self.assertEqual(calls[1]['arguments']['path'], 'b.txt')

    def test_run_returns_text_when_no_tool_calls(self):
        """Agent.run() should return the LLM text response when no tool calls are made."""
        from agent_core.agent import Agent
        a = Agent.__new__(Agent)
        a.max_iterations = 5
        a.history = []
        a.system_prompt = 'System prompt'
        a.llm = MagicMock()
        a.llm.complete.return_value = {'content': 'Halo, apa kabar?', 'tool_calls': []}
        result = a.run('Halo')
        self.assertEqual(result, 'Halo, apa kabar?')
        self.assertEqual(len(a.history), 2)  # user + assistant

    def test_run_executes_single_tool_call(self):
        """Agent.run() should execute a tool call and append observation."""
        from agent_core.agent import Agent
        a = Agent.__new__(Agent)
        a.max_iterations = 5
        a.history = []
        a.system_prompt = 'System prompt'
        a.llm = MagicMock()
        a.llm.complete.side_effect = [
            {'content': 'TOOL: write_file\nARGS: {"path": "x.txt"}\nCONTENT:\nisi file', 'tool_calls': []},
            {'content': 'Selesai menulis file.', 'tool_calls': []},
        ]
        a.tools = {}

        # Register a mock write_file tool
        from tools.tool import Tool
        mock_tool = MagicMock(spec=Tool)
        mock_tool.return_value = {'status': 'success', 'message': 'Wrote x.txt'}
        a.tools['write_file'] = mock_tool

        result = a.run('Tulis file x.txt')
        self.assertIn('Selesai menulis file.', result)
        mock_tool.assert_called_once()
        args = mock_tool.call_args[0][0]
        self.assertEqual(args['path'], 'x.txt')
        self.assertEqual(args['content'], 'isi file')
