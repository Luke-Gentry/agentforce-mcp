# stdlib
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 3p
import httpx
from httpx import Response

logger = logging.getLogger(__name__)


class MCPRecorder:
    """A class to intercept and record HTTP requests made through httpx clients."""

    def __init__(self, cassette_dir: str = "cassettes"):
        """Initialize the recorder with a directory to store cassettes.

        Args:
            cassette_dir: Directory where request/response cassettes will be stored
        """
        self.cassette_dir = Path(cassette_dir)
        self.cassette_dir.mkdir(parents=True, exist_ok=True)

    async def do_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Response:
        """Record and execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: The URL to make the request to
            params: Query parameters
            json_body: JSON body data
            **kwargs: Additional arguments to pass to httpx.Client.request

        Returns:
            The httpx Response object
        """
        # Create a unique filename for this request
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{method.lower()}_{Path(url).name}.json"
        cassette_path = self.cassette_dir / filename

        # Log the request
        logger.info(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Query parameters: {params}")
        if json_body:
            logger.debug(f"Request body: {json_body}")

        # Make the actual request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                **kwargs,
            )

        # Record the request and response
        cassette_data = {
            "request": {
                "method": method,
                "url": url,
                "params": params,
                "json": json_body,
                "headers": dict(response.request.headers),
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
            },
            "timestamp": timestamp,
        }

        # Save to file
        with open(cassette_path, "w") as f:
            json.dump(cassette_data, f, indent=2)

        logger.info(f"Request recorded to {cassette_path}")
        return response
