


import unittest
# Test minimal for the local AI coding agent.

class TestAgentLoop(unittest.TestCase):
    def test_agent_imports(self):
        from agent_core.agent import Agent
        assert Agent is not None
