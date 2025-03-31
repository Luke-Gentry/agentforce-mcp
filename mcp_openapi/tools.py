# stdlib
import re
from typing import Any, Union, Callable
from collections import defaultdict
from itertools import chain

# 3p
from pydantic import BaseModel

# project
from mcp_openapi import parser

# Imports for the tool functions
from pydantic import Field  # noqa: F401
from mcp.server.fastmcp import Context  # noqa: F401

# Maximum number of characters to include in enum descriptions
MAX_ENUM_DESCRIPTION_LENGTH = 100


class ToolParameter(BaseModel):
    name: str
    type: str
    default: Any
    request_body_field: str | None = None
    description: str | None = None


class Tool(BaseModel):
    name: str
    description: str
    query_params: list[ToolParameter]
    body_by_content_type: dict[str, list[ToolParameter]] | None = None
    method: str
    path: str

    @classmethod
    def from_operation(
        cls,
        path: str,
        method_name: str,
        operation: parser.Operation,
        exclude_params: list[str] = None,
    ) -> "Tool":
        exclude_params = exclude_params or []

        seen_params = set()
        query_params = []
        by_content_type = defaultdict(list)

        # Ensure array types come first with reversed sorting,
        # so we always pick the array name + type over the regular.
        for param in reversed(sorted(operation.parameters, key=lambda x: x.name)):
            dedup_name = cls._to_dedupe_name(param.name)
            if dedup_name in seen_params:
                continue

            # Build description with enum values if present
            description = param.description.strip() if param.description else ""
            if param.enum:
                enum_desc = f" Options: {', '.join(str(e) for e in param.enum)}"
                if len(enum_desc) > MAX_ENUM_DESCRIPTION_LENGTH:
                    # Truncate to fit within max length
                    enum_desc = (
                        f" Options: {', '.join(str(e) for e in param.enum[:2])}..."
                    )
                description = f"{description}{enum_desc}".strip()

            if param.name in exclude_params:
                continue

            query_params.append(
                ToolParameter(
                    name=cls._to_python_arg(param.name),
                    type=cls._to_python_type(param),
                    description=cls._to_python_description(description),
                    default=param.default,
                )
            )
            seen_params.add(dedup_name)

        # We'll map the request body to params but with a prefix so the tool
        # can put it in the body of the request.
        if operation.request_body_ and operation.request_body_.schema_:
            for param in operation.request_body_.schema_.properties:
                if param.any_of:
                    descriptions = []
                    for any_of in param.any_of:
                        if any_of.description:
                            descriptions.append(any_of.description)
                        elif any_of.properties:
                            descriptions.append(
                                f"Object with properties: {', '.join(p.name for p in any_of.properties)}"
                            )
                        elif any_of.type:
                            descriptions.append(any_of.type)
                    description = (
                        f"{param.description}, one of: ({') OR ('.join(descriptions)})"
                    )
                    by_content_type[operation.request_body_.content_type].append(
                        ToolParameter(
                            name=param.name,
                            type=cls._to_python_type(param),
                            description=cls._to_python_description(description),
                            request_body_field=param.name,
                            default="None",
                        )
                    )
                    seen_params.add(param.name)
                elif param.all_of:
                    for all_of in param.all_of:
                        props = all_of.properties if all_of.properties else [all_of]
                        for p in props:
                            by_content_type[
                                operation.request_body_.content_type
                            ].append(
                                ToolParameter(
                                    name=f"{param.name}_{p.name}",
                                    type=cls._to_python_type(p),
                                    description=cls._to_python_description(
                                        p.description
                                    ),
                                    default="None",
                                    request_body_field=f"{param.name}.{p.name}",
                                )
                            )
                elif param.properties:
                    # skipping multiple nested properties in tools for now.
                    pass
                else:
                    by_content_type[operation.request_body_.content_type].append(
                        ToolParameter(
                            name=param.name,
                            type=cls._to_python_type(param),
                            description=cls._to_python_description(param.description),
                            default="None",
                            request_body_field=param.name,
                        )
                    )
        return cls(
            name=cls._to_fn_name(operation.id),
            description=cls._to_python_description(
                operation.summary or operation.description or ""
            ),
            query_params=query_params,
            body_by_content_type=by_content_type,
            method=method_name,
            path=path,
        )

    def all_params(self) -> list[ToolParameter]:
        if not self.body_by_content_type:
            return self.query_params
        return self.query_params + list(
            chain.from_iterable(self.body_by_content_type.values())
        )

    @classmethod
    def _to_snake_case(cls, name: str) -> str:
        if not name:
            return name

        result = [name[0].lower()]

        for char in name[1:]:
            if char.isupper():
                result.append("_")
                result.append(char.lower())
            else:
                result.append(char)

        return "".join(result)

    @classmethod
    def _to_dedupe_name(cls, name: str) -> str:
        name = cls._to_snake_case(name)
        if name.endswith("[]"):
            name = name[:-2]
        return name

    @classmethod
    def _to_fn_name(cls, name: str) -> str:
        name = cls._to_snake_case(name)
        # replace invalid characters for a function name with a regex
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if name.startswith("_"):
            name = name[1:]
        return name

    @classmethod
    def _to_python_arg(cls, name: str) -> str:
        if name.endswith("[]"):
            name = f"{name[:-2]}s"
        return name

    @classmethod
    def _to_python_description(cls, description: str) -> str:
        if description:
            return description.replace("\n", " ").replace('"', "'").strip()
        return ""

    @classmethod
    def _to_python_type(cls, param: Union[parser.Parameter, parser.Schema]) -> str:
        py_type = "str"
        if (
            isinstance(param, parser.Parameter)
            and param.schema_
            and "oneOf" in param.schema_
        ):
            # Handle oneOf types by creating a Union type
            types = []
            for schema in param.schema_["oneOf"]:
                t = schema.get("type")
                if t == "string":
                    types.append("str")
                elif t == "integer":
                    types.append("int")
                elif t == "number":
                    types.append("float")
                elif t == "boolean":
                    types.append("bool")
                else:
                    types.append("Any")
            return f"Union[{', '.join(types)}]"
        elif isinstance(param.type, list):
            # Handle anyOf types by creating a Union type
            types = []
            for t in param.type:
                if t == "string":
                    types.append("str")
                elif t == "integer":
                    types.append("int")
                elif t == "number":
                    types.append("float")
                elif t == "boolean":
                    types.append("bool")
                else:
                    types.append("Any")
            return f"Union[{', '.join(types)}]"
        elif param.type == "string":
            py_type = "str"
        elif param.type == "integer":
            py_type = "int"
        elif param.type == "number":
            py_type = "float"
        elif param.type == "boolean":
            py_type = "bool"

        if hasattr(param, "name") and param.name.endswith("[]"):
            py_type = f"list[{py_type}]"

        return py_type


def tools_from_spec(spec: parser.Spec, forward_query_params: list[str]) -> list[Tool]:
    tools = []
    for path in spec.paths:
        for method_name, operation in [
            ("GET", path.get),
            ("POST", path.post),
            ("PUT", path.put),
            ("DELETE", path.delete),
            ("PATCH", path.patch),
        ]:
            if not operation:
                continue

            tools.append(
                Tool.from_operation(
                    path.path,
                    method_name,
                    operation,
                    exclude_params=forward_query_params,
                )
            )

    return tools


# This function is used by the tool functions.
def _set_body_field(request_body_field: str, body_dict: dict, value: Any):
    parts = request_body_field.split(".")
    current = body_dict
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def get_tool_function_body(tool: Tool) -> str:
    param_fields = []
    for param in tool.all_params():
        param_str = f"{param.name}: {param.type}"
        field_parts = []
        if param.description:
            field_parts.append(f'description="{param.description}"')
        # Quote string defaults
        default_value = (
            f'"{param.default}"' if isinstance(param.default, str) else param.default
        )
        field_parts.append(f"default={default_value}")
        param_str += f" = Field({', '.join(field_parts)})"
        param_fields.append(param_str)

    # Build the request body field assignments
    body_assignments = []
    if tool.body_by_content_type:
        for content_type, params in tool.body_by_content_type.items():
            for param in params:
                if content_type == "application/x-www-form-urlencoded":
                    body_assignments.append(
                        f'    form_data["{param.request_body_field}"] = {param.name}'
                    )
                else:
                    body_assignments.append(
                        f'    _set_body_field("{param.request_body_field}", json_body, {param.name})'
                    )

    body_assignments_str = "\n".join(body_assignments)

    return f"""async def {tool.name}(
        ctx: Context,
        {",\n        ".join(param_fields)}
    ) -> dict:
    \"\"\"{tool.description}\"\"\"
    base_url = ctx.request_context.lifespan_context.base_url
    proxy = ctx.request_context.lifespan_context.proxy
    params = {{ {', '.join(f'"{p.name}": {p.name}' for p in tool.query_params)} }}
    form_data = {{}}
    json_body = {{}}
{body_assignments_str}

    response = await proxy.do_request(
        request=ctx.request_context.request,
        method="{tool.method}",
        url=f"{{base_url}}{tool.path}",
        params=params,
        form_data=form_data,
        json_body=json_body,
    )
    return response.text"""


def create_tool_function_exec(tool: Tool) -> Callable:
    """Create a tool function from a tool object. This uses exec() to create the function which
    is somewhat clunky but works with all the typing we want.
    Note: There's a WIP version that's avoiding the exec() but not yet ready for use.
    """
    # Execute the function definition
    local_vars = {}
    exec(get_tool_function_body(tool), globals(), local_vars)
    return local_vars[tool.name]
