"""
General and infrastructure API route tests.
Replaced legacy stub-based tests from phase 1 with live tests for / and /health.
"""


def test_home_route(client):
    """Verify root greeting route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Student API is Running Successfully!" in response.data


def test_health_route(client):
    """Verify health endpoint pings real database successfully."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_legacy_students_route_empty(client):
    """Verify legacy /students route returns 200 and list."""
    response = client.get("/students")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_404_handling(client):
    """Verify 404 handler returns consistent JSON structure."""
    response = client.get("/non-existent-route")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_405_handling(client):
    """Verify 405 handler returns consistent JSON structure."""
    response = client.post("/health")
    assert response.status_code == 405
    assert response.get_json()["error"] == "Method not allowed"
