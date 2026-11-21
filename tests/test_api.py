"""
General and infrastructure API route tests.
Updated in Phase 3: "/" is now the academic performance dashboard page.
"""


def test_home_route(client):
    """Verify root route renders the academic dashboard HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"Academic Performance Dashboard" in response.data


def test_health_route(client):
    """Verify health endpoint pings real database successfully."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_404_handling_api(client):
    """Verify 404 handler for API routes returns consistent JSON."""
    response = client.get("/api/non-existent-route")
    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()


def test_404_handling_web(client):
    """Verify 404 handler for browser routes renders friendly 404 HTML template."""
    response = client.get("/non-existent-web-page")
    assert response.status_code == 404
    assert "text/html" in response.content_type
    assert b"Page Not Found" in response.data


def test_405_handling(client):
    """Verify 405 handler returns consistent JSON structure for API endpoints."""
    response = client.post("/health")
    assert response.status_code == 405
    assert response.is_json
    assert response.get_json()["error"] == "Method not allowed"
