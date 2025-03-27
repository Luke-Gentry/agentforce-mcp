from pydantic import BaseModel
from mcp_openapi import parser


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
