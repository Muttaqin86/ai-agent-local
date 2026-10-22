# AI Coding Agent (Local)

Agent coding pakai model AI lokal (Gemma via Ollama).

## Fitur
- Generate kode & perbaiki bug pakai model lokal
- Interaksi file sistem: read, write, search, glob
- Eksekusi perintah shell
- Loop agent: think -> tool -> observe -> repeat

## Prasyarat
- Python 3.11+
- Ollama; install model: `ollama pull gemma3:4b` (atau gemma3:1b/12b)

## Setup
```bash
pip install -r requirements.txt
python -m agent_core.cli "tulis fungsi faktorial di python"
```

## Struktur
```
agent_coding/
  agent_core/    # inti agent, loop, tool registry
  tools/         # tool aksi (bash, read, write, search, glob)
  config/        # config model
  scripts/       # skrip utilitas
  tests/         # uji coba
  logs/
```
