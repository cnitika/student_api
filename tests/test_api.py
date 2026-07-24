import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Student API is Running Successfully!" in response.data


def test_get_students(client):
    response = client.get('/students')
    assert response.status_code == 200
    assert response.get_json()["message"] == "Students route works"


def test_create_student_missing_fields(client):
    response = client.post('/students', json={"name": "John"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_student_no_body(client):
    response = client.post('/students')
    assert response.status_code == 400


@patch('app.get_connection')
def test_create_student_success(mock_get_connection, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 1
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    response = client.post('/students', json={
        "name": "John Doe",
        "email": "john@example.com",
        "course": "CS"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"


@patch('app.get_connection')
def test_update_student(mock_get_connection, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    response = client.patch('/students/1', json={"course": "Math"})
    assert response.status_code == 200
    assert response.get_json()["message"] == "Student updated successfully"


def test_update_student_missing_course(client):
    response = client.patch('/students/1', json={})
    assert response.status_code == 400


@patch('app.get_connection')
def test_delete_student(mock_get_connection, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    response = client.delete('/students/1')
    assert response.status_code == 204
