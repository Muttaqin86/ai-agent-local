import argparse
import logging
import sys

from .agent import Agent
from .config import load_config

from tools.tool import Tool
from tools.file_tool import read_file, write_file, glob_files, edit_file
from tools.bash_tool import bash_run
from tools.search_tool import search_code

logger = logging.getLogger(__name__)



def build_parser():
    parser = argparse.ArgumentParser(description="Local AI coding agent")
    parser.add_argument("prompt", help="User prompt / task")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--base-url", default=None, help="Override Ollama base URL")
    parser.add_argument("--max-iterations", type=int, default=None, help="Override max iterations")
    parser.add_argument("--temperature", type=float, default=None, help="Override temperature")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser



def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(name)s %(message)s")
    config = load_config()
    tools = {
        'write_file': Tool(
            name='write_file',
            description='Tulis konten ke file. PERINGATAN: akan MENGHAPUS dan menimpa SELURUH isi file jika file sudah ada. Gunakan hanya untuk file BARU atau penggantian total. Args: path (str), content (str).',
            func=write_file,
        ),
        'read_file': Tool(
            name='read_file',
            description='Baca isi file. Args: path (str), limit (int, optional).',
            func=read_file,
        ),
        'glob_files': Tool(
            name='glob_files',
            description='Cari file sesuai pola glob. Args: pattern (str).',
            func=glob_files,
        ),
        'bash_run': Tool(
            name='bash_run',
            description='Eksekusi perintah shell. Args: command (str).',
            func=bash_run,
        ),
        'search_code': Tool(
            name='search_code',
            description='Cari teks di dalam file repositori. Args: pattern (str).',
            func=search_code,
        ),
        'edit_file': Tool(
            name='edit_file',
            description='Ganti teks dalam file. Args: path (str), old_str (str), new_str (str), replace_all (bool, optional).',
            func=edit_file,
        ),
    }
    agent = Agent(
        model_name=args.model or config["model"]["name"],
        base_url=args.base_url or config["model"]["base_url"],
        tools=tools,
        max_iterations=args.max_iterations or config["run"].get("max_iterations", 50),
        temperature=args.temperature if args.temperature is not None else config["model"].get("temperature", 0.2),
    )
    try:
        response = agent.run(args.prompt)
        print(response)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.exception("Agent run failed: %s", exc)
        print("Agent error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

