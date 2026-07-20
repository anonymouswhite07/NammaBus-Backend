import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_route():
    """Verifies that the API launches successfully and returns welcome metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "version" in data["data"]

def test_openapi_json():
    """Verifies that the Swagger OpenAPI schema generates without compile/syntax errors."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "info" in schema
