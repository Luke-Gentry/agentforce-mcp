#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import Optional

from mcp_openapi.parser import Config


def parse_command(args: argparse.Namespace) -> None:
    """Handle the parse command."""
    if args.file and args.url:
        print("Error: Cannot specify both --file and --url")
        return

    if not args.file and not args.url:
        print("Error: Must specify either --file or --url")
        return

    if args.file:
        config = Config.from_file(
            args.file,
            args.routes,
            use_cache=False,
        )
    else:
        config = Config.from_url(args.url, args.routes, use_cache=False)

    print(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP OpenAPI CLI tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse an OpenAPI spec")
    parse_parser.add_argument(
        "--file",
        help="Path to OpenAPI spec file",
        type=str,
    )
    parse_parser.add_argument(
        "--url",
        help="URL to OpenAPI spec",
        type=str,
    )
    parse_parser.add_argument(
        "--routes",
        nargs="+",
        required=True,
        help="Route patterns to include (regex)",
    )

    args = parser.parse_args()

    if args.command == "parse":
        parse_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
