# LLM client abstraction

from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger(__name__)

PROVIDER_DESC = {
    "ollama": "local Ollama instance",
    "openai": "OpenAI API",
    "anthropic": "Anthropic API",
    "gemini": "Google Gemini API",
}

class LLMClient:
    """Client LLM yang bisa bekerja dengan banyak provider."""
    def __init__(
        self,
        model_name: str,
        provider: str = "ollama",
        api_key: str = "",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
    ):
        self.model_name = model_name
        self.provider = provider.lower().strip()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature

        if self.provider not in PROVIDER_DESC:
            logger.warning(
                "Provider %s not recognized, falling back to 'ollama'",
                self.provider,
            )
            self.provider = "ollama"

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
    ) -> dict:
        provider = self.provider

        if provider == "ollama":
            return self._call_ollama(messages, tools)
        elif provider == "openai":
            return self._call_openai(messages, tools)
        elif provider == "anthropic":
            return self._call_anthropic(messages, tools)
        elif provider == "gemini":
            return self._call_gemini(messages, tools)
        else:
            logger.warning("Unknown provider '%s', using ollama", provider)
            return self._call_ollama(messages, tools)
    def _call_anthropic(self, messages, tools):
        if not self.api_key:
            return {
                "content": "",
                "tool_calls": [],
                "error": "API key not set for Anthropic provider. Set AGENT_API_KEY env var.",
            }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Anthropic-Version": "2023-06-01",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 1000,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_anthropic_response(data)
        except Exception as exc:
            logger.error("Anthropic request failed: %s", exc)
            return {"content": "", "tool_calls": [], "error": str(exc)}

    def _parse_anthropic_response(self, data):
        content = ""
        if data.get("content") and len(data["content"]) > 0:
            first = data["content"][0]
            if isinstance(first, dict):
                content = first.get("text", "")
            elif isinstance(first, str):
                content = first
        tool_calls = []
        return {"content": content, "tool_calls": tool_calls}
# LLM client abstraction

from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger(__name__)

PROVIDER_DESC = {
    "ollama": "local Ollama instance",
    "openai": "OpenAI API",
    "anthropic": "Anthropic API",
    "gemini": "Google Gemini API",
}

class LLMClient:
    """Client LLM yang bisa bekerja dengan banyak provider."""
    def __init__(
        self,
        model_name: str,
        provider: str = "ollama",
        api_key: str = "",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
    ):
        self.model_name = model_name
        self.provider = provider.lower().strip()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature

        if self.provider not in PROVIDER_DESC:
            logger.warning(
                "Provider %s not recognized, falling back to 'ollama'",
                self.provider,
            )
            self.provider = "ollama"

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
    ) -> dict:
        provider = self.provider

        if provider == "ollama":
            return self._call_ollama(messages, tools)
        elif provider == "openai":
            return self._call_openai(messages, tools)
        elif provider == "anthropic":
            return self._call_anthropic(messages, tools)
        elif provider == "gemini":
            return self._call_gemini(messages, tools)
        else:
            logger.warning("Unknown provider '%s', using ollama", provider)
            return self._call_ollama(messages, tools)
    def _call_anthropic(self, messages, tools):
        if not self.api_key:
            return {
                "content": "",
                "tool_calls": [],
                "error": "API key not set for Anthropic provider. Set AGENT_API_KEY env var.",
            }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Anthropic-Version": "2023-06-01",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 1000,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_anthropic_response(data)
        except Exception as exc:
            logger.error("Anthropic request failed: %s", exc)
            return {"content": "", "tool_calls": [], "error": str(exc)}

    def _parse_anthropic_response(self, data):
        content = ""
        if data.get("content") and len(data["content"]) > 0:
            first = data["content"][0]
            if isinstance(first, dict):
                content = first.get("text", "")
            elif isinstance(first, str):
                content = first
        tool_calls = []
        return {"content": content, "tool_calls": tool_calls}

    # ---------- OLLAMA ----------

    def _call_ollama(self, messages, tools):
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(
                self.base_url + "/api/chat",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_ollama_response(data)
        except Exception as exc:
            logger.error("Ollama request failed: %s", exc)
            return {"content": "", "tool_calls": [], "error": str(exc)}

    def _parse_ollama_response(self, data):
        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            tool_calls.append(
                {
                    "name": tc.get("function", {}).get("name"),
                    "arguments": tc.get("function", {}).get("arguments"),
                }
            )
        return {"content": content, "tool_calls": tool_calls}

    # ---------- OPENAI ----------

    def _call_openai(self, messages, tools):
        if not self.api_key:
            return {
                "content": "",
                "tool_calls": [],
                "error": "API key not set for OpenAI provider. Set AGENT_API_KEY env var.",
            }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_openai_response(data)
        except Exception as exc:
            logger.error("OpenAI request failed: %s", exc)
            return {"content": "", "tool_calls": [], "error": str(exc)}

    def _parse_openai_response(self, data):
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        tool_calls = []
        if tools:
            tcalls = message.get("tool_calls", [])
            for tc in tcalls:
                tool_calls.append(
                    {
                        "name": tc.get("function", {}).get("name"),
                        "arguments": tc.get("function", {}).get("arguments"),
                    }
                )
        return {"content": content, "tool_calls": tool_calls}

    # ---------- ANTHROPIC ----------

    # Sudah ada, lewati

    # ---------- GEMINI ----------

    def _call_gemini(self, messages, tools):
        if not self.api_key:
            return {
                "content": "",
                "tool_calls": [],
                "error": "API key not set for Gemini provider. Set AGENT_API_KEY env var.",
            }
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "contents": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_gemini_response(data)
        except Exception as exc:
            logger.error("Gemini request failed: %s", exc)
            return {"content": "", "tool_calls": [], "error": str(exc)}

    def _parse_gemini_response(self, data):
        text = data.get("text", "")
        return {"content": text, "tool_calls": []}
