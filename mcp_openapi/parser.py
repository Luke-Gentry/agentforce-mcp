# stdlib
from typing import Dict, List, Optional, Any
import re
import logging
import pickle
import hashlib
from pathlib import Path

# 3p
import aiopenapi3
import pathlib
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create cache directory in the user's home directory
CACHE_DIR = Path.home() / ".mcp-openapi" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

"""

- Only supporting inline properties, single reference or allOf
- Not supporting oneOf, anyOf, not
"""


class SchemaProperty(BaseModel):
    name: str
    type: str
    items: Optional["SchemaProperty"] = None
    properties: Optional[List["SchemaProperty"]] = None


class Schema(BaseModel):
    name: str
    properties: Optional[List[SchemaProperty]] = None


class Parameter(BaseModel):
    name: str
    in_: str = Field(alias="in")
    required: bool = False
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    description: Optional[str] = None
    deprecated: Optional[bool] = None
    allowEmptyValue: Optional[bool] = None
    style: Optional[str] = None
    explode: Optional[bool] = None
    allowReserved: Optional[bool] = None
    type: Optional[str] = None
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None


class Response(BaseModel):
    description: str
    content: Optional[Dict[str, Any]] = None
    schema_: Optional[Schema] = Field(default=None)
    format: str = "text/plain"


class RequestBody(BaseModel):
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    required: bool = False
    schema_: Optional[Schema] = Field(default=None)
    encoding: Optional[Dict[str, Dict[str, Any]]] = None


class Operation(BaseModel):
    id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = []
    request_body_: Optional[RequestBody] = Field(default=None)
    responses: Dict[str, Response]


class Path(BaseModel):
    path: str
    get: Optional[Operation] = None
    post: Optional[Operation] = None
    put: Optional[Operation] = None
    delete: Optional[Operation] = None
    patch: Optional[Operation] = None


class Config:
    @classmethod
    def from_file(
        cls,
        file_path: str,
        path_patterns: list[str],
        base_path=pathlib.Path("").absolute(),
    ):
        # Create cache key from file path and patterns
        cache_key = hashlib.md5(
            f"{file_path}:{','.join(sorted(path_patterns))}".encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.pickle"

        if cache_file.exists():
            logger.info(f"Loading cached OpenAPI spec from {cache_file}")
            with open(cache_file, "rb") as f:
                return pickle.load(f)

        logger.info(f"Cold loading OpenAPI spec from {file_path}")
        api = aiopenapi3.OpenAPI.load_file(
            file_path,
            file_path,
            loader=aiopenapi3.FileSystemLoader(base_path),
        )
        config = cls._from_api(api, path_patterns)

        # Cache the result
        with open(cache_file, "wb") as f:
            pickle.dump(config, f)

        return config

    @classmethod
    def from_url(cls, url: str, path_patterns: list[str]):
        # Create cache key from URL and patterns
        cache_key = hashlib.md5(
            f"{url}:{','.join(sorted(path_patterns))}".encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.pickle"

        if cache_file.exists():
            logger.info(f"Loading cached OpenAPI spec from {cache_file}")
            with open(cache_file, "rb") as f:
                return pickle.load(f)

        logger.info(f"Cold loading OpenAPI spec from {url}")
        api = aiopenapi3.OpenAPI.load_sync(
            url,
            loader=aiopenapi3.FileSystemLoader(pathlib.Path("")),
        )
        config = cls._from_api(api, path_patterns)

        # Cache the result
        with open(cache_file, "wb") as f:
            pickle.dump(config, f)

        return config

    @classmethod
    def _from_api(cls, api: aiopenapi3.OpenAPI, path_patterns: list[str]):
        paths = []

        compiled_patterns = [re.compile(pattern) for pattern in path_patterns]
        for path, path_item in api.paths.paths.items():
            # Check if path matches any of the patterns
            if not any(pattern.match(path) for pattern in compiled_patterns):
                continue

            processed_path = Path(path=path)
            if path_item.get:
                processed_path.get = cls._process_operation(path, path_item.get, api)
            if path_item.post:
                processed_path.post = cls._process_operation(path, path_item.post, api)
            if path_item.put:
                processed_path.put = cls._process_operation(path, path_item.put, api)
            if path_item.delete:
                processed_path.delete = cls._process_operation(
                    path, path_item.delete, api
                )
            if path_item.patch:
                processed_path.patch = cls._process_operation(
                    path, path_item.patch, api
                )
            paths.append(processed_path)

        return cls(paths=paths)

    def __init__(self, paths: List[Path]):
        self.paths = paths

    @classmethod
    def _process_schema(cls, schema, api) -> Optional[Schema]:
        """Process schema and return a Schema model."""
        properties = []
        if hasattr(schema, "ref"):
            # Extract the schema name from the reference
            schema_name = schema.ref.split("/")[-1]
            resolved_schema = api.components.schemas[schema_name]
        else:
            schema_name = "inline"
            resolved_schema = schema

        if resolved_schema.allOf:
            for schema in resolved_schema.allOf:
                properties.extend(cls._process_schema(schema, api).properties)
        elif resolved_schema.properties:
            for prop_name, prop_schema in resolved_schema.properties.items():
                prop_type = prop_schema.type or "object"
                prop = SchemaProperty(name=prop_name, type=prop_type)

                if prop_type == "array" and hasattr(prop_schema, "items"):
                    item_schema = prop_schema.items
                    if hasattr(item_schema, "ref"):
                        item_name = item_schema.ref.split("/")[-1]
                        resolved_item_schema = api.components.schemas[item_name]
                        if resolved_item_schema.type == "object":
                            item_properties = []
                            for (
                                item_prop_name,
                                item_prop_schema,
                            ) in resolved_item_schema.properties.items():
                                item_prop_type = item_prop_schema.type or "object"
                                item_prop = SchemaProperty(
                                    name=item_prop_name, type=item_prop_type
                                )
                                if item_prop_type == "object":
                                    nested_schema = cls._process_schema(
                                        item_prop_schema, api
                                    )
                                    if nested_schema:
                                        item_prop.properties = nested_schema.properties
                                item_properties.append(item_prop)
                            prop.items = SchemaProperty(
                                name=item_name,
                                type="object",
                                properties=item_properties,
                            )
                    else:
                        prop.items = SchemaProperty(
                            name="item", type=item_schema.type or "object"
                        )

                elif prop_type == "object":
                    if hasattr(prop_schema, "ref"):
                        nested_schema = cls._process_schema(prop_schema, api)
                        if nested_schema:
                            prop.properties = nested_schema.properties
                    else:
                        nested_properties = []
                        for (
                            nested_name,
                            nested_schema,
                        ) in prop_schema.properties.items():
                            nested_prop = SchemaProperty(
                                name=nested_name, type=nested_schema.type or "object"
                            )
                            if nested_schema.type == "object":
                                nested_schema_result = cls._process_schema(
                                    nested_schema, api
                                )
                                if nested_schema_result:
                                    nested_prop.properties = (
                                        nested_schema_result.properties
                                    )
                            nested_properties.append(nested_prop)
                        prop.properties = nested_properties

                properties.append(prop)
        elif resolved_schema.type == "array":
            properties.append(
                SchemaProperty(
                    name="inline",
                    type="array",
                    items=SchemaProperty(
                        name="item",
                        type=resolved_schema.items.type or "object",
                        properties=cls._process_schema(
                            resolved_schema.items, api
                        ).properties,
                    ),
                )
            )
        return Schema(
            name=schema_name,
            properties=properties,
        )

    @classmethod
    def _process_operation(cls, path_name, operation, api) -> Operation:
        """Process operation and return an Operation model."""
        processed_params = []
        for param in operation.parameters:
            param_dict = {
                "name": param.name,
                "in": param.in_,
                "required": bool(getattr(param, "required", False)),
                "description": getattr(param, "description", None),
                "deprecated": getattr(param, "deprecated", None),
                "allowEmptyValue": getattr(param, "allowEmptyValue", None),
                "style": getattr(param, "style", None),
                "explode": getattr(param, "explode", None),
                "allowReserved": getattr(param, "allowReserved", None),
                "type": param.schema_.type,
            }

            # Add enum and default if they exist in the schema
            if hasattr(param.schema_, "enum"):
                param_dict["enum"] = param.schema_.enum
                param_dict["required"] = True
            if hasattr(param.schema_, "default"):
                param_dict["default"] = param.schema_.default

            processed_params.append(Parameter(**param_dict))

        processed_responses = {}
        for status_code, response in operation.responses.items():
            schema = None
            format = "text/plain"
            if response.content and "application/json" in response.content:
                schema = cls._process_schema(
                    response.content["application/json"].schema_, api
                )
                format = "application/json"
            processed_responses[status_code] = Response(
                description=response.description,
                content=response.content,
                schema_=schema,
                format=format,
            )

        # Process request body if present
        request_body = None
        if operation.requestBody:
            schema = None
            encoding = None
            content_type = None

            # Handle form-encoded content
            if (
                operation.requestBody.content
                and "application/x-www-form-urlencoded" in operation.requestBody.content
            ):
                content = operation.requestBody.content[
                    "application/x-www-form-urlencoded"
                ]
                if hasattr(content, "schema_"):
                    schema = cls._process_schema(content.schema_, api)
                if hasattr(content, "encoding"):
                    # Convert encoding object to dictionary
                    encoding = {}
                    for field_name, encoding_obj in content.encoding.items():
                        encoding[field_name] = {
                            "explode": getattr(encoding_obj, "explode", None),
                            "style": getattr(encoding_obj, "style", None),
                            "allowReserved": getattr(
                                encoding_obj, "allowReserved", None
                            ),
                            "contentType": getattr(encoding_obj, "contentType", None),
                        }
                content_type = "application/x-www-form-urlencoded"
            # Handle JSON content
            elif (
                operation.requestBody.content
                and "application/json" in operation.requestBody.content
            ):
                content_schema = operation.requestBody.content[
                    "application/json"
                ].schema_
                schema = cls._process_schema(content_schema, api)
                content_type = "application/json"

            request_body = RequestBody(
                description=getattr(operation.requestBody, "description", None),
                content=operation.requestBody.content,
                required=bool(getattr(operation.requestBody, "required", False)),
                schema_=schema,
                encoding=encoding,
            )

        return Operation(
            id=operation.operationId or path_name,
            summary=operation.summary,
            description=operation.description,
            parameters=processed_params,
            request_body_=request_body,
            responses=processed_responses,
        )

    def __repr__(self):
        output = []

        def _repr_schema(schema: Schema, indent: str = "") -> str:
            """Helper function to format schema details recursively."""
            output = []
            if schema.properties:
                output.append(f"{indent}Properties:")
                for prop in schema.properties:
                    output.append(f"{indent}  - {prop.name}: {prop.type}")
                    if prop.items:
                        output.append(f"{indent}    Items: {prop.items.name}")
                        if prop.items.properties:
                            output.append(f"{indent}    Properties:")
                            for item_prop in prop.items.properties:
                                output.append(
                                    f"{indent}      - {item_prop.name}: {item_prop.type}"
                                )
                    elif prop.properties:
                        output.append(f"{indent}    Properties:")
                        for nested_prop in prop.properties:
                            output.append(
                                f"{indent}      - {nested_prop.name}: {nested_prop.type}"
                            )

            return "\n".join(output)

        for path in self.paths:
            if path.get:
                output.append(f"GET: {path.get.summary}")
                output.append("Parameters:")
                for param in path.get.parameters:
                    output.append(f"  - {param.name} ({param.in_})")
                output.append("Responses:")
                for status_code, response in path.get.responses.items():
                    output.append(f"  - {status_code}: {response.description}")
                    if response.schema_:
                        output.append(f"    Schema: {response.schema_.name}")
                        output.append(_repr_schema(response.schema_, "    "))

            for method, operation in [
                ("POST", path.post),
                ("PUT", path.put),
                ("DELETE", path.delete),
                ("PATCH", path.patch),
            ]:
                if operation:
                    output.append(f"{method}: {operation.summary}")
                    if operation.request_body_:
                        output.append("Request body:")
                        if operation.request_body_.schema_:
                            output.append(
                                f"  Schema: {operation.request_body_.schema_.name}"
                            )
                            output.append(
                                _repr_schema(operation.request_body_.schema_, "  ")
                            )
                    output.append("Responses:")
                    for status_code, response in operation.responses.items():
                        output.append(f"  - {status_code}: {response.description}")
                        if response.schema_:
                            output.append(f"    Schema: {response.schema_.name}")
                            output.append(_repr_schema(response.schema_, "    "))

        return "\n".join(output)
