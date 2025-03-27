# stdlib
import logging
import sys
import yaml
from typing import Dict, AsyncIterator
from dataclasses import dataclass
from contextlib import asynccontextmanager

# 3p
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# project
from mcp_openapi.parser import Config
from mcp_openapi.tools import tools_from_config, Tool

# Imports for the tool functions
from pydantic import Field  # noqa: F401
from mcp.server.fastmcp import Context  # noqa: F401
import httpx  # noqa: F401


logger = logging.getLogger(__name__)


class ServerManager:
    def __init__(self, config_path: str = "servers.yaml"):
        self.config_path = config_path
        self.servers: Dict[str, FastMCP] = {}
        self.tools: Dict[str, list[Tool]] = {}
        self.routes = []
        self.setup_endpoints()
        self.load_config()

    def setup_endpoints(self):
        """Set up Starlette endpoints"""

        async def get_all_tools(request):
            tools_by_namespace = {}
            for namespace, tools in self.tools.items():
                tools_by_namespace[namespace] = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": [param.model_dump() for param in tool.parameters],
                    }
                    for tool in tools
                ]
            return JSONResponse(content=tools_by_namespace)

        async def get_namespace_tools(request):
            namespace = request.path_params["namespace"]
            if namespace not in self.tools:
                return JSONResponse(
                    content={"error": f"Namespace '{namespace}' not found"},
                    status_code=404,
                )
            return JSONResponse(
                content=[
                    {"name": tool.name, "description": tool.description}
                    for tool in self.tools[namespace]
                ]
            )

        # Add routes for tools endpoints
        self.routes.extend(
            [
                Route("/tools", get_all_tools),
                Route("/tools/{namespace}", get_namespace_tools),
            ]
        )

    def load_config(self):
        """Load and parse the servers configuration file."""
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_path}: {e}")
            sys.exit(1)

    async def start_servers(self):
        """Start all configured servers."""
        for server_config in self.config["servers"]:
            await self.start_server(server_config)

    async def start_server(self, server_config: dict):
        """Start a single server based on its configuration."""
        namespace = server_config["namespace"]
        name = server_config["name"]
        url = server_config["url"]
        base_url = server_config["base_url"]
        paths = server_config["paths"]

        logger.info(f"Starting server for {name} ({namespace})")

        try:
            # Load the OpenAPI config
            config = (
                Config.from_file(url[7:], paths)
                if url.startswith("file://")
                else Config.from_url(url, paths)
            )

            # Create the AppContext class
            @dataclass
            class AppContext:
                base_url: str

            # Create the lifespan manager
            @asynccontextmanager
            async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
                """Manage application lifecycle with type-safe context"""
                try:
                    yield AppContext(base_url=base_url)
                finally:
                    pass

            # Create the FastMCP instance
            mcp = FastMCP(
                name,
                lifespan=app_lifespan,
                sse_path=f"/{namespace}/sse",
                message_path=f"/{namespace}/messages/",
                debug=True,
            )

            tools = tools_from_config(config)
            self.tools[namespace] = tools

            # Create tools for each path
            for tool in tools:
                # Create the tool function with explicit parameters
                def create_tool_function(tool):
                    # Build the function signature with explicit parameters
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

                    # Create the function body with proper indentation
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

                # Create the tool function and add it to the FastMCP instance
                tool_function = create_tool_function(tool)
                mcp.tool(
                    name=tool.name,
                    description=tool.description,
                )(tool_function)

                logger.info(f"{name} - tool: {tool.name} - {tool.description}")

            # Store the server instance
            self.servers[namespace] = mcp

            # Add MCP routes to our routes list
            mcp_app = mcp.sse_app()
            self.routes.extend(mcp_app.routes)

            logger.info(f"Started server for {name} ({namespace})")

        except Exception as e:
            logger.exception(f"Failed to start server for {name}: {e}")

    async def stop_servers(self):
        """Stop all running servers."""
        for namespace, server in self.servers.items():
            logger.info(f"Stopping server for {namespace}")
            # Add any cleanup logic here if needed
        self.servers.clear()
        self.routes = []  # Clear routes when stopping servers

    def get_app(self) -> Starlette:
        """Get the Starlette application with all routes."""
        return Starlette(routes=self.routes)
