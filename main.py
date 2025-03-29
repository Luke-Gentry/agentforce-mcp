#!/usr/bin/env python3


import argparse
import logging
import os
import asyncio

# 3p
from watchdog.observers import Observer
import uvicorn

# project
from mcp_openapi.server_manager import ServerManager
from mcp_openapi.file_watcher import ConfigFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="MCP Server Manager")
    parser.add_argument(
        "--config", default="servers.yaml", help="Path to servers configuration file"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on"
    )
    args = parser.parse_args()

    server_manager = ServerManager(args.config)

    # Get the current event loop
    loop = asyncio.get_running_loop()

    # Set up file watching with the event loop
    observer = Observer()
    observer.schedule(
        ConfigFileHandler(server_manager, loop),
        path=os.path.dirname(os.path.abspath(args.config)),
        recursive=False,
    )
    observer.start()

    try:
        # Start all servers
        await server_manager.start_servers()

        # Get the Starlette app and run it
        app = server_manager.get_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=args.port, loop=loop)
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        await server_manager.stop_servers()
        observer.stop()
        observer.join()


if __name__ == "__main__":
    asyncio.run(main())
