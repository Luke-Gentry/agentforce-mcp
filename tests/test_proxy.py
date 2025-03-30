# stdlib
import pytest

# 3p
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from httpx import Response, AsyncClient

# local
from mcp_openapi.proxy import MCPProxy


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    mock_client = AsyncMock(spec=AsyncClient)
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"test": "response"}'
    mock_response.request = MagicMock()
    mock_response.request.headers = {}
    mock_client.request.return_value = mock_response
    return mock_client


@pytest.fixture
def proxy(tmp_path, mock_httpx_client):
    """Create a proxy instance and mock client."""
    return MCPProxy(
        client_builder=lambda: mock_httpx_client,
    )


@pytest.fixture
def mock_request():
    """Create a mock request with headers."""
    request = Request(
        scope={
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer test-token"),
                (b"content-type", b"application/json"),
                (b"x-custom-header", b"test-value"),
            ],
        }
    )
    return request


@pytest.mark.asyncio
async def test_proxy_params(proxy, mock_request, mock_httpx_client):
    """Test that query parameters are correctly passed in the request."""
    url = "https://api.example.com/test"
    params = {"key1": "value1", "key2": "value2"}

    response = await proxy.do_request(
        request=mock_request,
        method="GET",
        url=url,
        params=params,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct parameters
    mock_httpx_client.request.assert_called_once_with(
        method="GET",
        url=url,
        params=params,
        json=None,
        headers={},
        timeout=None,
    )


@pytest.mark.asyncio
async def test_proxy_forward_headers(proxy, mock_request, mock_httpx_client):
    """Test that only specified headers are forwarded."""
    proxy.forward_headers = ["authorization", "x-custom-header"]
    proxy.timeout = 0.5

    url = "https://api.example.com/test"

    response = await proxy.do_request(
        request=mock_request,
        method="GET",
        url=url,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct headers
    mock_httpx_client.request.assert_called_once_with(
        method="GET",
        url=url,
        params=None,
        json=None,
        headers={
            "authorization": "Bearer test-token",
            "x-custom-header": "test-value",
        },
        timeout=0.5,
    )


@pytest.mark.asyncio
async def test_proxy_forward_query_params(proxy, mock_httpx_client):
    """Test that only specified query parameters are forwarded."""
    proxy.forward_query_params = {"x-open-weather-app-id": "appid"}

    url = "https://api.example.com/test"
    params = {
        "other_param": "will_also_be_included",
    }
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer test-token"),
                (b"content-type", b"application/json"),
                (b"x-custom-header", b"test-value"),
                (b"x-open-weather-app-id", b"weather123"),
            ],
        }
    )

    response = await proxy.do_request(
        request=mock_request,
        method="GET",
        url=url,
        params=params,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with only the specified parameters
    mock_httpx_client.request.assert_called_once_with(
        method="GET",
        url=url,
        json=None,
        params={
            "appid": "weather123",
            "other_param": "will_also_be_included",
        },
        headers={},
        timeout=None,
    )


@pytest.mark.asyncio
async def test_proxy_json_body(proxy, mock_request, mock_httpx_client):
    """Test that JSON body is correctly passed."""
    url = "https://api.example.com/test"
    json_body = {"test": "data"}

    response = await proxy.do_request(
        request=mock_request,
        method="POST",
        url=url,
        json_body=json_body,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct JSON body
    mock_httpx_client.request.assert_called_once_with(
        method="POST",
        url=url,
        params=None,
        json=json_body,
        headers={},
        timeout=None,
    )
