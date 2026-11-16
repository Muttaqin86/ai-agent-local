"""Memory persistence for the AI coding agent."""

import json
import os
from pathlib import Path

# Default memory file location (home directory)
MEMORY_DIR = Path.home() / ".agent"
MEMORY_FILE = MEMORY_DIR / "memory.json"


class AgentMemory:
    """Memori persisten untuk AI coding agent."""

    def __init__(self, memory_file: Path = MEMORY_FILE):
        self.memory_file = memory_file
        self.ensure_dir()

    def ensure_dir(self):
        """Buat direktori memory jika belum ada."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Muat memory dari file JSON."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "conversation_history": [],
            "project_context": {},
            "last_run": None,
        }

    def save(self, data: dict):
        """Simpan memory ke file JSON."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error("Gagal menyimpan memory: %s", e)

    def update_conversation(self, user_input: str, agent_response: str):
        """Tambah entri ke riwayat percakapan."""
        data = self.load()
        data["conversation_history"].append({
            "user": user_input,
            "agent": agent_response,
            "timestamp": os.path.getmtime(self.memory_file) if self.memory_file.exists() else None,
        }
        # Batas maksimal 50 entri terbaru
        if len(data["conversation_history"]) > 50:
            data["conversation_history"] = data["conversation_history"][-50:]
        self.save(data)

    def set_project_context(self, key: str, value: str):
        """Simpan konteks proyek (key-value)."""
        data = self.load()
        data["project_context"][key] = value
        self.save(data)

    def get_project_context(self, key: str = None) -> dict:
        """Ambil konteks proyek."""
        data = self.load()
        if key:
            return data["project_context"].get(key)
        return data["project_context"]

    def clear(self):
        """Bersihkan memory."""
        self.save({"conversation_history": [], "project_context": {}, "last_run": None})