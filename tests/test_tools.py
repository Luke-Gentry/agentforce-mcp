import inspect
from unittest.mock import AsyncMock, patch

import pytest

from mcp_openapi.tools import (
    Tool,
    ToolParameter,
    create_tool_function_exec,
    create_tool_function_noexec,
)
from mcp_openapi.proxy import MCPProxy

from starlette.requests import Request


@pytest.fixture
def mock_tool():
    """Create a simple mock tool for testing"""
    return Tool(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="param1", type="str", description="First parameter", default="None"
            ),
            ToolParameter(
                name="param2",
                type="int",
                description="Second parameter",
                default="None",
            ),
            ToolParameter(
                name="j_body_param",
                type="dict",
                description="Body parameter",
                default="None",
            ),
        ],
        method="POST",
        path="/test/path",
    )


@pytest.fixture
def mock_context():
    """Create a mock context with base_url"""

    class MockContext:
        class RequestContext:
            class LifespanContext:
                base_url = "http://test.com"
                proxy = MCPProxy(record=False)

            lifespan_context = LifespanContext()
            request = Request(
                scope={
                    "type": "http",
                    "method": "GET",
                    "path": "/test",
                }
            )

        request_context = RequestContext()

    return MockContext()


@pytest.fixture
def weather_tool():
    """Create a weather API tool with enums and defaults"""
    return Tool(
        name="get_forecast",
        description="Get weather forecast",
        parameters=[
            ToolParameter(
                name="temperature_unit",
                type="str",
                description="Temperature unit Options: celsius, fahrenheit",
                default="celsius",
            ),
            ToolParameter(
                name="wind_speed_unit",
                type="str",
                description="Wind speed unit Options: kmh, ms, mph, kn",
                default="kmh",
            ),
            ToolParameter(
                name="timeformat",
                type="str",
                description="Time format Options: iso8601, unixtime",
                default="iso8601",
            ),
        ],
        method="GET",
        path="/v1/forecast",
    )


@pytest.mark.asyncio
async def test_tool_function_noexec(mock_tool, mock_context):
    """Test the noexec tool function creation"""
    # Create the tool function
    tool_func = create_tool_function_noexec(mock_tool)

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.text = '{"result": "success"}'

    # Create an AsyncMock for the client itself
    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_response
    mock_client_instance.aclose = AsyncMock()  # Add mock for aclose method

    with patch("httpx.AsyncClient") as mock_client:
        # Return the mock client instance directly instead of using __aenter__
        mock_client.return_value = mock_client_instance

        # Test function execution
        result = await tool_func(
            mock_context, param1="test", param2=123, j_body_param={"key": "value"}
        )

        # Verify the request was made correctly
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args[1]

        assert call_args["method"] == "POST"
        assert call_args["url"] == "http://test.com/test/path"
        assert call_args["params"] == {"param1": "test", "param2": 123}
        assert call_args["json"] == {"body_param": {"key": "value"}}
        assert result == '{"result": "success"}'


@pytest.mark.asyncio
async def test_tool_function_exec(mock_tool, mock_context):
    """Test the exec tool function creation"""
    # Create the tool function
    tool_func = create_tool_function_exec(mock_tool)

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.text = '{"result": "success"}'

    # Create an AsyncMock for the client itself
    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_response
    mock_client_instance.aclose = AsyncMock()  # Add mock for aclose method

    with patch("httpx.AsyncClient") as mock_client:
        # Return the mock client instance directly instead of using __aenter__
        mock_client.return_value = mock_client_instance

        # Test function execution
        result = await tool_func(
            mock_context, param1="test", param2=123, j_body_param={"key": "value"}
        )

        # Verify the request was made correctly
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args[1]
        assert call_args["method"] == "POST"
        assert call_args["url"] == "http://test.com/test/path"
        assert call_args["params"] == {"param1": "test", "param2": 123}
        assert call_args["json"] == {"body_param": {"key": "value"}}
        assert result == '{"result": "success"}'


def test_tool_parameter_conversion():
    """Test that tool parameters are correctly converted to Python types"""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="string_param",
                type="str",
                description="String parameter",
                default="None",
            ),
            ToolParameter(
                name="int_param",
                type="int",
                description="Integer parameter",
                default="None",
            ),
            ToolParameter(
                name="float_param",
                type="float",
                description="Float parameter",
                default="None",
            ),
            ToolParameter(
                name="bool_param",
                type="bool",
                description="Boolean parameter",
                default="None",
            ),
            ToolParameter(
                name="array_param",
                type="list[str]",
                description="Array parameter",
                default="None",
            ),
        ],
        method="GET",
        path="/test/path",
    )

    # Create function using noexec method
    tool_func = create_tool_function_noexec(tool)

    # Verify parameter types
    sig = inspect.signature(tool_func)
    assert (
        sig.parameters["string_param"].annotation
        == 'Field(description="String parameter", default=None)'
    )
    assert (
        sig.parameters["int_param"].annotation
        == 'Field(description="Integer parameter", default=None)'
    )
    assert (
        sig.parameters["float_param"].annotation
        == 'Field(description="Float parameter", default=None)'
    )
    assert (
        sig.parameters["bool_param"].annotation
        == 'Field(description="Boolean parameter", default=None)'
    )
    assert (
        sig.parameters["array_param"].annotation
        == 'Field(description="Array parameter", default=None)'
    )


def test_tool_parameter_enums_and_defaults(weather_tool):
    """Test that tool parameters correctly handle enums and defaults"""
    # Create function using noexec method
    tool_func = create_tool_function_noexec(weather_tool)

    # Verify parameter types and descriptions
    sig = inspect.signature(tool_func)

    # Test temperature_unit parameter
    temp_param = sig.parameters["temperature_unit"]
    assert (
        temp_param.annotation
        == 'Field(description="Temperature unit Options: celsius, fahrenheit", default=celsius)'
    )

    # Test wind_speed_unit parameter
    wind_param = sig.parameters["wind_speed_unit"]
    assert (
        wind_param.annotation
        == 'Field(description="Wind speed unit Options: kmh, ms, mph, kn", default=kmh)'
    )

    # Test timeformat parameter
    time_param = sig.parameters["timeformat"]
    assert (
        time_param.annotation
        == 'Field(description="Time format Options: iso8601, unixtime", default=iso8601)'
    )


@pytest.mark.asyncio
async def test_weather_tool_execution(weather_tool, mock_context):
    """Test the weather tool function execution with enums and defaults"""
    # Create the tool function
    tool_func = create_tool_function_exec(weather_tool)

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.text = '{"temperature": 20, "wind_speed": 10}'

    # Create an AsyncMock for the client itself
    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_response
    mock_client_instance.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value = mock_client_instance

        # Test function execution with default values
        result = await tool_func(mock_context)

        # Verify the request was made with default values
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args[1]
        assert call_args["method"] == "GET"
        assert call_args["url"] == "http://test.com/v1/forecast"

        # Check that params contain Field objects with correct defaults
        params = call_args["params"]
        assert params["temperature_unit"].default == "celsius"
        assert params["wind_speed_unit"].default == "kmh"
        assert params["timeformat"].default == "iso8601"

        assert result == '{"temperature": 20, "wind_speed": 10}'

        # Test with custom values
        result = await tool_func(
            mock_context,
            temperature_unit="fahrenheit",
            wind_speed_unit="mph",
            timeformat="unixtime",
        )

        # Verify the request was made with custom values
        assert mock_client_instance.request.call_count == 2
        call_args = mock_client_instance.request.call_args[1]
        params = call_args["params"]
        assert params["temperature_unit"] == "fahrenheit"
        assert params["wind_speed_unit"] == "mph"
        assert params["timeformat"] == "unixtime"
