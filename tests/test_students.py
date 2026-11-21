"""
Integration tests for Students API endpoints against student_test_db.
"""

def sample_student_payload(roll_no="CS2026001", email="student1@college.edu"):
    return {
        "roll_no": roll_no,
        "student_name": "Aditya Verma",
        "email": email,
        "department": "Computer Science & Engineering",
        "course": "B.Tech CSE",
        "academic_year": "2025-2026",
        "semester": 4
    }


def test_create_student_success(client):
    payload = sample_student_payload()
    response = client.post("/api/students", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] is not None
    assert data["roll_no"] == "CS2026001"
    assert data["student_name"] == "Aditya Verma"
    assert data["email"] == "student1@college.edu"
    assert data["semester"] == 4


def test_create_student_missing_fields(client):
    response = client.post("/api/students", json={"student_name": "No Roll"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_student_no_json(client):
    response = client.post("/api/students", data="not-json")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_student_invalid_email(client):
    payload = sample_student_payload()
    payload["email"] = "invalid-email-address"
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "Invalid email format" in response.get_json()["error"]


def test_create_student_invalid_semester(client):
    payload = sample_student_payload()
    payload["semester"] = 15  # Out of range 1-12
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "Semester must be an integer between 1 and 12" in response.get_json()["error"]


def test_create_student_duplicate_roll_no(client):
    client.post("/api/students", json=sample_student_payload(roll_no="DUP01", email="first@test.edu"))
    response = client.post("/api/students", json=sample_student_payload(roll_no="DUP01", email="second@test.edu"))
    assert response.status_code == 409
    assert "already exists" in response.get_json()["error"]


def test_create_student_duplicate_email(client):
    client.post("/api/students", json=sample_student_payload(roll_no="ROLL01", email="same@test.edu"))
    response = client.post("/api/students", json=sample_student_payload(roll_no="ROLL02", email="same@test.edu"))
    assert response.status_code == 409
    assert "already exists" in response.get_json()["error"]


def test_get_student_by_id(client):
    created = client.post("/api/students", json=sample_student_payload()).get_json()
    student_id = created["id"]

    response = client.get(f"/api/students/{student_id}")
    assert response.status_code == 200
    assert response.get_json()["id"] == student_id


def test_get_student_by_id_404(client):
    response = client.get("/api/students/99999")
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"].lower()


def test_list_and_search_students(client):
    client.post("/api/students", json=sample_student_payload(roll_no="CS001", email="a@test.edu"))
    client.post("/api/students", json={
        "roll_no": "IT002",
        "student_name": "Priya Singh",
        "email": "priya@test.edu",
        "department": "Information Technology",
        "course": "B.Tech IT",
        "academic_year": "2025-2026",
        "semester": 6
    })

    # List all
    all_res = client.get("/api/students")
    assert all_res.status_code == 200
    assert len(all_res.get_json()) == 2

    # Search by roll_no
    search_roll = client.get("/api/students?q=IT002")
    assert len(search_roll.get_json()) == 1
    assert search_roll.get_json()[0]["student_name"] == "Priya Singh"

    # Search by partial name
    search_name = client.get("/api/students?q=priya")
    assert len(search_name.get_json()) == 1
    assert search_name.get_json()[0]["roll_no"] == "IT002"


def test_patch_student_success(client):
    created = client.post("/api/students", json=sample_student_payload()).get_json()
    student_id = created["id"]

    response = client.patch(f"/api/students/{student_id}", json={
        "course": "M.Tech CSE",
        "semester": 5
    })
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["course"] == "M.Tech CSE"
    assert updated["semester"] == 5
    assert updated["student_name"] == created["student_name"]


def test_patch_student_empty_body(client):
    created = client.post("/api/students", json=sample_student_payload()).get_json()
    response = client.patch(f"/api/students/{created['id']}", json={})
    assert response.status_code == 400
    assert "No valid fields" in response.get_json()["error"]


def test_patch_student_404(client):
    response = client.patch("/api/students/99999", json={"course": "New Course"})
    assert response.status_code == 404


def test_patch_student_duplicate_email(client):
    client.post("/api/students", json=sample_student_payload(roll_no="R1", email="user1@test.edu"))
    s2 = client.post("/api/students", json=sample_student_payload(roll_no="R2", email="user2@test.edu")).get_json()

    # Try updating s2 to have user1's email
    response = client.patch(f"/api/students/{s2['id']}", json={"email": "user1@test.edu"})
    assert response.status_code == 409
    assert "already in use" in response.get_json()["error"]


def test_delete_student_success(client):
    created = client.post("/api/students", json=sample_student_payload()).get_json()
    student_id = created["id"]

    del_res = client.delete(f"/api/students/{student_id}")
    assert del_res.status_code == 204

    # Verify student is gone
    get_res = client.get(f"/api/students/{student_id}")
    assert get_res.status_code == 404


def test_delete_student_404(client):
    response = client.delete("/api/students/99999")
    assert response.status_code == 404
