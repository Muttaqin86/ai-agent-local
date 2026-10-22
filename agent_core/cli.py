import argparse
import logging
import sys

from .agent import Agent
from .config import load_config

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
    agent = Agent(
        model_name=args.model or config["model"]["name"],
        base_url=args.base_url or config["model"]["base_url"],
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

