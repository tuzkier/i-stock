#!/usr/bin/env python3
"""Prints: export COGNEE_TOKEN='...' for bash eval. See cognee_token.resolve_bearer_token."""
import json
import sys

try:
    from cognee_token import resolve_bearer_token
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cognee_token import resolve_bearer_token


def main() -> None:
    if len(sys.argv) < 2:
        print("ERROR: missing config path", file=sys.stderr)
        sys.exit(1)
    config_path = sys.argv[1]
    try:
        tok = resolve_bearer_token(config_path)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"export COGNEE_TOKEN={json.dumps(tok)}")


if __name__ == "__main__":
    main()
