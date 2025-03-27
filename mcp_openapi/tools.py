# stdlib
import inspect
import types

# 3p
import httpx
from pydantic import BaseModel

# project
from mcp_openapi import parser


# Imports for the tool functions
from pydantic import Field  # noqa: F401
from mcp.server.fastmcp import Context  # noqa: F401
import httpx  # noqa: F401


class ToolParameter(BaseModel):
    name: str
    type: str
    default: str | None = None
    description: str | None = None


class Tool(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter]
    method: str
    path: str

    @classmethod
    def from_operation(
        cls, path: str, method_name: str, operation: parser.Operation
    ) -> "Tool":
        # Ensure array types come first with reversed sorting,
        # so we always pick the array name + type over the regular.
        seen_params = set()
        tool_params = []

        for param in reversed(sorted(operation.parameters, key=lambda x: x.name)):
            dedup_name = cls._to_dedupe_name(param.name)
            if dedup_name in seen_params:
                continue

            tool_params.append(
                ToolParameter(
                    name=cls._to_python_arg(param.name),
                    type=cls._to_python_type(param),
                    description=param.description.strip(),
                    default="None" if not param.required else None,
                )
            )
            seen_params.add(dedup_name)

        # We'll map the request body to params but with a prefix so the tool
        # can put it in the body of the request.
        if operation.request_body_:
            for param in operation.request_body_.schema_.properties:
                if param.properties:
                    for nested_param in param.properties:
                        tool_params.append(
                            ToolParameter(
                                name=cls._to_python_arg(f"j_{nested_param.name}"),
                                type=cls._to_python_type(nested_param),
                                description="",
                                default="None",
                            )
                        )
                else:
                    tool_params.append(
                        ToolParameter(
                            name=cls._to_python_arg(f"j_{param.name}"),
                            type=cls._to_python_type(param),
                            description="",
                            default="None",
                        )
                    )

        return cls(
            name=cls._to_snake_case(operation.id),
            description=operation.summary,
            parameters=tool_params,
            method=method_name,
            path=path,
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
    def _to_python_arg(cls, name: str) -> str:
        if name.endswith("[]"):
            name = f"{name[:-2]}s"
        return name

    @classmethod
    def _to_python_type(cls, param: parser.Parameter) -> str:
        py_type = "str"
        if param.type == "string":
            py_type = "str"
        elif param.type == "integer":
            py_type = "int"
        elif param.type == "number":
            py_type = "float"
        elif param.type == "boolean":
            py_type = "bool"

        if param.name.endswith("[]"):
            py_type = f"list[{py_type}]"

        return py_type


def tools_from_config(config: parser.Config) -> list[Tool]:
    tools = []
    for path in config.paths:
        for method_name, operation in [
            ("GET", path.get),
            ("POST", path.post),
            ("PUT", path.put),
            ("DELETE", path.delete),
            ("PATCH", path.patch),
        ]:
            if not operation:
                continue

            tools.append(Tool.from_operation(path.path, method_name, operation))

    return tools


def create_tool_function_noexec(tool):
    # Define a template function that will be used as the code template
    async def template_tool_function(ctx, *args, **kwargs):
        """Template function whose code will be reused"""
        # Extract base URL from context
        base_url = ctx.request_context.lifespan_context.base_url

        # Build params and json data from kwargs
        # We'll replace this logic at runtime with the actual parameter handling
        params = {}
        json = {}

        # Make the API request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=tool.method,
                url=f"{base_url}{tool.path}",
                params=params,
                json=json,
            )
            return response.text

    # Create a real function that processes the specific parameters
    async def real_implementation(ctx, **kwargs):
        # Process parameters based on tool definition
        params = {
            p.name: kwargs[p.name]
            for p in tool.parameters
            if not p.name.startswith("j_") and p.name in kwargs
        }
        json_data = {
            p.name[2:]: kwargs[p.name]
            for p in tool.parameters
            if p.name.startswith("j_") and p.name in kwargs
        }

        # Make the API request
        base_url = ctx.request_context.lifespan_context.base_url
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=tool.method,
                url=f"{base_url}{tool.path}",
                params=params,
                json=json_data,
            )
            return response.text

    # Create parameter objects for the signature
    parameters = [
        inspect.Parameter(
            name="ctx",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation="Context",  # Use string annotation to avoid ForwardRef issues
        )
    ]

    # Add tool-specific parameters
    for param in tool.parameters:
        default = inspect.Parameter.empty
        if hasattr(param, "default") and param.default is not None:
            default = param.default

        parameters.append(
            inspect.Parameter(
                name=param.name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=param.type,  # Use string type from tool definition
                default=default,
            )
        )

    # Create signature with these parameters
    sig = inspect.Signature(parameters=parameters)

    # Clone the code object from the template function
    code = template_tool_function.__code__

    # Create a function with the original code but new name and defaults
    # This gives us the basic structure, we'll modify more attributes later
    new_func = types.FunctionType(code, globals(), name=tool.name, argdefs=())

    # Make it an async function by setting the correct flags
    setattr(
        new_func,
        "__code__",
        types.CodeType(
            code.co_argcount,
            code.co_posonlyargcount,
            code.co_kwonlyargcount,
            code.co_nlocals,
            code.co_stacksize,
            code.co_flags,  # Preserve async flags
            code.co_code,
            code.co_consts,
            code.co_names,
            code.co_varnames,
            code.co_filename,
            tool.name,  # Set function name
            code.co_firstlineno,
            code.co_lnotab,
            code.co_freevars,
            code.co_cellvars,
        ),
    )

    # Create a wrapper that delegates to our real implementation
    async def wrapper_func(ctx, *args, **kwargs):
        return await real_implementation(ctx, **kwargs)

    # Set function attributes
    wrapper_func.__name__ = tool.name
    wrapper_func.__doc__ = tool.description
    wrapper_func.__signature__ = sig
    wrapper_func.__annotations__ = {
        "ctx": "Context",
        "return": dict,
        **{p.name: p.type for p in tool.parameters},
    }

    return wrapper_func


def create_tool_function_exec(tool):
    params = []
    for param in tool.parameters:
        param_str = f"{param.name}: {param.type}"
        if param.description or param.default:
            field_parts = []
            if param.description:
                field_parts.append(f'description="{param.description}"')
            if param.default:
                field_parts.append(f"default={param.default}")
            param_str += f" = Field({', '.join(field_parts)})"
        params.append(param_str)

    # Build the function signature with explicit parameters
    # We have to use exec() for now to make this work with all the typing we want.
    body = f"""async def {tool.name}(
        ctx: Context,
        {', '.join(params)}
    ) -> dict:
    \"\"\"{tool.description}\"\"\"
    base_url = ctx.request_context.lifespan_context.base_url
    params = {{ {', '.join(f'"{p.name}": {p.name}' for p in tool.parameters if not p.name.startswith('j_'))} }}
    json = {{ {', '.join(f'"{p.name[2:]}": {p.name}' for p in tool.parameters if p.name.startswith('j_'))} }}

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="{tool.method}",
            url=f"{{base_url}}{tool.path}",
            params=params,
            json=json,
        )
        return response.text"""

    # Execute the function definition
    local_vars = {}
    exec(body, globals(), local_vars)
    return local_vars[tool.name]
