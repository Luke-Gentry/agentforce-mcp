#!/usr/bin/env python3

import argparse

from mcp_openapi.parser import Spec
from mcp_openapi.tools import tools_from_spec


def parse_command(args: argparse.Namespace) -> None:
    """Handle the parse command."""
    if args.file and args.url:
        print("Error: Cannot specify both --file and --url")
        return

    if not args.file and not args.url:
        print("Error: Must specify either --file or --url")
        return

    if args.file:
        spec = Spec.from_file(
            args.file,
            args.routes,
            use_cache=False,
        )
    else:
        spec = Spec.from_url(args.url, args.routes, use_cache=False)

    print(spec)


def tools_command(args: argparse.Namespace) -> None:
    """Handle the tools command."""
    if args.file and args.url:
        print("Error: Cannot specify both --file and --url")
        return

    if not args.file and not args.url:
        print("Error: Must specify either --file or --url")
        return

    if args.file:
        spec = Spec.from_file(
            args.file,
            args.routes,
            use_cache=False,
        )
    else:
        spec = Spec.from_url(args.url, args.routes, use_cache=False)

    tools = tools_from_spec(spec, args.forward_query_params)
    for tool in tools:
        print(f"\nTool: {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Method: {tool.method}")
        print(f"Path: {tool.path}")
        print("Parameters:")
        for param in tool.parameters:
            print(f"  - {param.name}: {param.type}")
            if param.description:
                print(f"    Description: {param.description}")


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

    # Tools command
    tools_parser = subparsers.add_parser("tools", help="Display tool definitions")
    tools_parser.add_argument(
        "--file",
        help="Path to OpenAPI spec file",
        type=str,
    )
    tools_parser.add_argument(
        "--url",
        help="URL to OpenAPI spec",
        type=str,
    )
    tools_parser.add_argument(
        "--routes",
        nargs="+",
        required=True,
        help="Route patterns to include (regex)",
    )
    tools_parser.add_argument(
        "--forward-query-params",
        nargs="+",
        help="Query parameters to forward to the tool",
    )

    args = parser.parse_args()

    if args.command == "parse":
        parse_command(args)
    elif args.command == "tools":
        tools_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
