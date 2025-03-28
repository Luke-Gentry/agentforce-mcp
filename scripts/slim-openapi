#!/usr/bin/env python3

import argparse
import json
import re
import sys
import yaml
from typing import Dict, List, Set, Any
from mcp_openapi.parser import Config


def load_openapi_spec(input_path: str) -> Dict[str, Any]:
    """Load OpenAPI spec from file or URL."""
    try:
        if input_path.startswith(("http://", "https://")):
            import requests

            response = requests.get(input_path)
            response.raise_for_status()
            content = response.text
        else:
            with open(input_path, "r") as f:
                content = f.read()

        # Try to parse as YAML first, then JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)
    except Exception as e:
        print(f"Error loading OpenAPI spec: {e}", file=sys.stderr)
        sys.exit(1)


def get_referenced_schemas(spec: Dict[str, Any], paths: Dict[str, Any]) -> Set[str]:
    """Extract all schema references from the given paths."""
    schema_refs = set()
    processed_schemas = set()

    def collect_refs(obj: Any) -> None:
        if isinstance(obj, dict):
            # Handle direct $ref
            if "$ref" in obj:
                ref = obj["$ref"]
                if ref.startswith("#/components/schemas/"):
                    schema_refs.add(ref)
                    # If we haven't processed this schema yet, look through it for more references
                    schema_name = ref.split("/")[-1]
                    if schema_name not in processed_schemas:
                        processed_schemas.add(schema_name)
                        if "components" in spec and "schemas" in spec["components"]:
                            if schema_name in spec["components"]["schemas"]:
                                collect_refs(spec["components"]["schemas"][schema_name])

            # Handle composition keywords
            for keyword in ["anyOf", "allOf", "oneOf", "not"]:
                if keyword in obj:
                    if isinstance(obj[keyword], list):
                        for item in obj[keyword]:
                            collect_refs(item)
                    else:
                        collect_refs(obj[keyword])

            # Handle properties
            if "properties" in obj:
                for prop in obj["properties"].values():
                    collect_refs(prop)

            # Handle items in arrays
            if "items" in obj:
                collect_refs(obj["items"])

            # Handle additionalProperties
            if "additionalProperties" in obj:
                collect_refs(obj["additionalProperties"])

            # Handle responses
            if "responses" in obj:
                for response in obj["responses"].values():
                    if "content" in response:
                        for content_type in response["content"].values():
                            if "schema" in content_type:
                                collect_refs(content_type["schema"])

            # Handle requestBody
            if "requestBody" in obj:
                if "content" in obj["requestBody"]:
                    for content_type in obj["requestBody"]["content"].values():
                        if "schema" in content_type:
                            collect_refs(content_type["schema"])

            # Handle x-expansionResources
            if "x-expansionResources" in obj:
                collect_refs(obj["x-expansionResources"])

            # Recursively check all other values
            for value in obj.values():
                collect_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                collect_refs(item)

    # Collect references from paths
    for path in paths.values():
        collect_refs(path)

    return schema_refs


def slim_openapi_spec(
    spec: Dict[str, Any], route_patterns: List[str]
) -> Dict[str, Any]:
    """Slim down OpenAPI spec to only include specified routes and their dependencies."""
    # Compile regex patterns
    patterns = [re.compile(pattern) for pattern in route_patterns]

    # Create new spec with basic structure
    slimmed_spec = {
        "openapi": spec.get("openapi", "3.0.0"),
        "info": spec.get("info", {}),
        "paths": {},
        "components": {"schemas": {}},
    }

    # Filter paths based on patterns
    for path, path_item in spec.get("paths", {}).items():
        if any(pattern.match(path) for pattern in patterns):
            slimmed_spec["paths"][path] = path_item

    # Get all referenced schemas from the filtered paths, but use the full spec
    schema_refs = get_referenced_schemas(spec, slimmed_spec["paths"])

    # Add referenced schemas to the output
    for ref in schema_refs:
        schema_name = ref.split("/")[-1]
        if "components" in spec and "schemas" in spec["components"]:
            if schema_name in spec["components"]["schemas"]:
                slimmed_spec["components"]["schemas"][schema_name] = spec["components"][
                    "schemas"
                ][schema_name]

    return slimmed_spec


def main():
    parser = argparse.ArgumentParser(
        description="Slim down OpenAPI spec to specified routes"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-f",
        "--open-api-spec",
        help="Path to OpenAPI spec file (YAML or JSON)",
    )
    group.add_argument(
        "-u",
        "--open-api-spec-url",
        help="URL to OpenAPI spec file (YAML or JSON)",
    )
    parser.add_argument(
        "--routes",
        nargs="+",
        required=True,
        help="Regular expressions matching the routes to keep",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        required=True,
        help="Output file path for the slimmed OpenAPI spec",
    )

    args = parser.parse_args()

    # Load the OpenAPI spec
    input_path = args.open_api_spec or args.open_api_spec_url
    spec = load_openapi_spec(input_path)

    # Slim down the spec
    slimmed_spec = slim_openapi_spec(spec, args.routes)

    # Write the output
    try:
        with open(args.output_file, "w") as f:
            if args.output_file.endswith(".json"):
                json.dump(slimmed_spec, f, indent=2)
            else:
                yaml.dump(slimmed_spec, f, sort_keys=False)
        print(f"Successfully wrote slimmed OpenAPI spec to {args.output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

    # Try to parse it back out
    print("Ensuring slimmed spec is parseable...")
    config = Config.from_file(args.output_file, args.routes)
    print(config)


if __name__ == "__main__":
    main()
