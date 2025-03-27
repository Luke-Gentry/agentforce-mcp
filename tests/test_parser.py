import json
import pytest
from mcp_openapi.parser import Config


@pytest.fixture
def sample_openapi_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/api/v1/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"},
                            "description": "Number of users to return",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            },
            "/api/v1/users/{userId}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }


@pytest.fixture
def sample_openapi_spec_with_refs():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
                "UserInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
            },
            "parameters": {
                "userIdParam": {
                    "name": "userId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
            },
        },
        "paths": {
            "/api/v1/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                },
            },
            "/api/v1/users/{userId}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "parameters": [{"$ref": "#/components/parameters/userIdParam"}],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                }
            },
        },
    }


def test_path_pattern_matching(tmp_path, sample_openapi_spec):
    # Create a temporary OpenAPI spec file
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    # Test exact path matching
    config = Config.from_file(str(spec_file), ["/api/v1/users$"], base_path=tmp_path)
    assert len(config.paths) == 1
    assert config.paths[0].path == "/api/v1/users"

    # Verify GET operation details
    get_op = config.paths[0].get
    assert get_op.id == "getUsers"
    assert get_op.summary == "Get all users"
    assert len(get_op.parameters) == 1
    assert get_op.parameters[0].name == "limit"
    assert get_op.parameters[0].in_ == "query"
    assert get_op.parameters[0].type == "integer"

    # Test regex pattern matching for path parameters
    config = Config.from_file(
        str(spec_file), [r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 1
    assert config.paths[0].path == "/api/v1/users/{userId}"

    # Verify path parameter operation
    get_op = config.paths[0].get
    assert get_op.id == "getUser"
    assert get_op.parameters[0].name == "userId"
    assert get_op.parameters[0].in_ == "path"
    assert get_op.parameters[0].required is True


def test_request_response_processing(tmp_path, sample_openapi_spec):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    config = Config.from_file(str(spec_file), ["/api/v1/users"], base_path=tmp_path)
    assert len(config.paths) == 2
    path = config.paths[0]

    # Test GET response schema
    get_response = path.get.responses["200"]
    assert get_response.format == "application/json"
    assert get_response.description == "Successful response"
    schema = get_response.schema_
    assert schema.properties[0].type == "array"
    assert schema.properties[0].items.type == "object"
    assert len(schema.properties[0].items.properties) == 2

    # Test POST request and response
    post_op = path.post
    assert post_op.request_body_.required is True
    request_schema = post_op.request_body_.schema_
    assert len(request_schema.properties) == 2
    assert {p.name for p in request_schema.properties} == {"name", "email"}
    assert all(p.type == "string" for p in request_schema.properties)

    # Test POST response
    post_response = post_op.responses["201"]
    assert post_response.format == "application/json"
    assert post_response.description == "User created successfully"
    response_schema = post_response.schema_
    assert len(response_schema.properties) == 2
    assert {p.name for p in response_schema.properties} == {"id", "name"}


def test_multiple_path_patterns(tmp_path, sample_openapi_spec):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    # Test matching multiple patterns
    config = Config.from_file(
        str(spec_file), [r"/api/v1/users", r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 2
    paths = {p.path for p in config.paths}
    assert paths == {"/api/v1/users", "/api/v1/users/{userId}"}

    # Verify all operations are properly loaded
    operations = []
    for path in config.paths:
        if path.get:
            operations.append(path.get.id)
        if path.post:
            operations.append(path.post.id)

    assert set(operations) == {"getUsers", "createUser", "getUser"}


def test_reference_resolution(tmp_path, sample_openapi_spec_with_refs):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec_with_refs, f)

    config = Config.from_file(str(spec_file), ["/api/v1/users"], base_path=tmp_path)
    assert len(config.paths) == 2
    path = config.paths[0]

    # Test GET response schema with resolved reference
    get_response = path.get.responses["200"]
    schema = get_response.schema_
    assert schema.properties[0].type == "array"
    items = schema.properties[0].items
    assert items.type == "object"
    assert len(items.properties) == 2
    assert {p.name for p in items.properties} == {"id", "name"}

    # Test POST request body with resolved reference
    post_op = path.post
    request_schema = post_op.request_body_.schema_
    assert len(request_schema.properties) == 2
    assert {p.name for p in request_schema.properties} == {"name", "email"}

    # Test POST response with resolved reference
    post_response = post_op.responses["201"]
    response_schema = post_response.schema_
    assert len(response_schema.properties) == 2
    assert {p.name for p in response_schema.properties} == {"id", "name"}


def test_parameter_reference_resolution(tmp_path, sample_openapi_spec_with_refs):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec_with_refs, f)

    config = Config.from_file(
        str(spec_file), [r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 1
    path = config.paths[0]

    # Test resolved parameter reference
    get_op = path.get
    assert len(get_op.parameters) == 1
    param = get_op.parameters[0]
    assert param.name == "userId"
    assert param.in_ == "path"
    assert param.required is True
    assert param.type == "string"
