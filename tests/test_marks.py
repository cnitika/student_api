"""
Integration tests for Subjects, Marks, and Academic Result APIs against student_test_db.
"""

def create_sample_student(client, roll_no="CS100", semester=5):
    res = client.post("/api/students", json={
        "roll_no": roll_no,
        "student_name": "Rahul Sharma",
        "email": f"{roll_no.lower()}@college.edu",
        "department": "Computer Science",
        "course": "B.Tech CSE",
        "academic_year": "2025-2026",
        "semester": semester
    })
    assert res.status_code == 201
    return res.get_json()


def create_sample_subject(client, code="CS501", name="DBMS", max_marks=100):
    res = client.post("/api/subjects", json={
        "subject_code": code,
        "subject_name": name,
        "max_marks": max_marks
    })
    assert res.status_code == 201
    return res.get_json()


# -------------------------------------------------------------
# Subjects Tests
# -------------------------------------------------------------
def test_create_and_get_subject(client):
    sub = create_sample_subject(client, code="CS501", name="Database Systems", max_marks=100)
    assert sub["id"] is not None
    assert sub["subject_code"] == "CS501"

    get_res = client.get(f"/api/subjects/{sub['id']}")
    assert get_res.status_code == 200
    assert get_res.get_json()["subject_code"] == "CS501"


def test_create_subject_duplicate_code(client):
    create_sample_subject(client, code="CS502", name="Python")
    res = client.post("/api/subjects", json={
        "subject_code": "CS502",
        "subject_name": "Another Python",
        "max_marks": 100
    })
    assert res.status_code == 409
    assert "already exists" in res.get_json()["error"]


def test_create_subject_invalid_max_marks(client):
    res = client.post("/api/subjects", json={
        "subject_code": "CS503",
        "subject_name": "Networks",
        "max_marks": 0
    })
    assert res.status_code == 400
    assert "greater than 0" in res.get_json()["error"]


def test_patch_subject(client):
    sub = create_sample_subject(client, code="CS504", name="OS", max_marks=100)
    res = client.patch(f"/api/subjects/{sub['id']}", json={"subject_name": "Operating Systems (Advanced)"})
    assert res.status_code == 200
    assert res.get_json()["subject_name"] == "Operating Systems (Advanced)"


def test_delete_subject_success(client):
    sub = create_sample_subject(client, code="CS505", name="Math", max_marks=100)
    res = client.delete(f"/api/subjects/{sub['id']}")
    assert res.status_code == 204


def test_delete_subject_with_marks_restricted(client):
    student = create_sample_student(client)
    sub = create_sample_subject(client, code="CS506", name="Algo", max_marks=100)

    # Add a mark record
    client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": sub["id"],
        "marks_obtained": 75
    })

    # Deleting subject must be rejected with 409
    del_res = client.delete(f"/api/subjects/{sub['id']}")
    assert del_res.status_code == 409
    assert "Cannot delete subject because student marks reference it" in del_res.get_json()["error"]


# -------------------------------------------------------------
# Marks Tests
# -------------------------------------------------------------
def test_add_marks_success(client):
    student = create_sample_student(client, semester=3)
    subject = create_sample_subject(client, code="CS301", name="DSA", max_marks=100)

    res = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 82
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["marks_obtained"] == 82.0
    assert data["semester"] == 3  # Defaulted to student's semester


def test_add_marks_validation_negative(client):
    student = create_sample_student(client)
    subject = create_sample_subject(client)

    res = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": -5
    })
    assert res.status_code == 400
    assert "cannot be negative" in res.get_json()["error"]


def test_add_marks_validation_exceeds_max(client):
    student = create_sample_student(client)
    subject = create_sample_subject(client, max_marks=100)

    res = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 105
    })
    assert res.status_code == 400
    assert "cannot exceed" in res.get_json()["error"]


def test_add_marks_non_numeric(client):
    student = create_sample_student(client)
    subject = create_sample_subject(client)

    res = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": "abc"
    })
    assert res.status_code == 400


def test_add_marks_unknown_student_404(client):
    subject = create_sample_subject(client)
    res = client.post("/api/students/99999/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 50
    })
    assert res.status_code == 404


def test_add_marks_unknown_subject_404(client):
    student = create_sample_student(client)
    res = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": 99999,
        "marks_obtained": 50
    })
    assert res.status_code == 404


def test_add_marks_duplicate_subject_same_semester(client):
    student = create_sample_student(client, semester=5)
    subject = create_sample_subject(client)

    res1 = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 70
    })
    assert res1.status_code == 201

    # Duplicate in same semester 5
    res2 = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 80
    })
    assert res2.status_code == 409
    assert "already exist" in res2.get_json()["error"]


def test_patch_and_delete_mark(client):
    student = create_sample_student(client)
    subject = create_sample_subject(client, max_marks=100)

    mark = client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 65
    }).get_json()

    # Update mark
    patch_res = client.patch(f"/api/marks/{mark['id']}", json={"marks_obtained": 85})
    assert patch_res.status_code == 200
    assert patch_res.get_json()["marks_obtained"] == 85.0

    # Delete mark
    del_res = client.delete(f"/api/marks/{mark['id']}")
    assert del_res.status_code == 204

    # Delete again 404
    del_404 = client.delete(f"/api/marks/{mark['id']}")
    assert del_404.status_code == 404


# -------------------------------------------------------------
# Academic Result Endpoint Integration Tests
# -------------------------------------------------------------
def test_get_result_no_marks_available(client):
    student = create_sample_student(client)
    res = client.get(f"/api/students/{student['id']}/result")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "Result Not Available"
    assert data["percentage"] is None


def test_get_result_spec_rahul_sharma_pass(client):
    """
    Spec verification:
    DBMS 85, Python 92, Computer Networks 78, Operating Systems 88, Mathematics 75 (each / 100)
    Expected result: total 418/500, 83.60%, grade A, PASS.
    """
    student = create_sample_student(client, roll_no="CS2025001", semester=5)
    s1 = create_sample_subject(client, code="CS501", name="DBMS", max_marks=100)
    s2 = create_sample_subject(client, code="CS502", name="Python", max_marks=100)
    s3 = create_sample_subject(client, code="CS503", name="Computer Networks", max_marks=100)
    s4 = create_sample_subject(client, code="CS504", name="Operating Systems", max_marks=100)
    s5 = create_sample_subject(client, code="CS505", name="Mathematics", max_marks=100)

    for sub, marks in [(s1, 85), (s2, 92), (s3, 78), (s4, 88), (s5, 75)]:
        client.post(f"/api/students/{student['id']}/marks", json={
            "subject_id": sub["id"],
            "semester": 5,
            "marks_obtained": marks
        })

    res = client.get(f"/api/students/{student['id']}/result?semester=5")
    assert res.status_code == 200
    data = res.get_json()

    assert data["total_obtained"] == 418.0
    assert data["total_max"] == 500.0
    assert data["percentage"] == 83.60
    assert data["grade"] == "A"
    assert data["status"] == "PASS"
    assert len(data["failed_subjects"]) == 0


def test_get_result_fail_one_subject_below_35_percent(client):
    student = create_sample_student(client, roll_no="CS2025002", semester=5)
    s1 = create_sample_subject(client, code="CS511", name="Subject 1", max_marks=100)
    s2 = create_sample_subject(client, code="CS512", name="Subject 2", max_marks=100)

    client.post(f"/api/students/{student['id']}/marks", json={"subject_id": s1["id"], "marks_obtained": 95})
    client.post(f"/api/students/{student['id']}/marks", json={"subject_id": s2["id"], "marks_obtained": 34.5})

    res = client.get(f"/api/students/{student['id']}/result")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "FAIL"
    assert len(data["failed_subjects"]) == 1
    assert data["failed_subjects"][0]["subject_code"] == "CS512"


def test_cascade_delete_student_removes_marks(client):
    student = create_sample_student(client)
    subject = create_sample_subject(client)

    client.post(f"/api/students/{student['id']}/marks", json={
        "subject_id": subject["id"],
        "marks_obtained": 75
    })

    # Delete student
    del_res = client.delete(f"/api/students/{student['id']}")
    assert del_res.status_code == 204

    # Subject can now be deleted because cascade deleted the marks record!
    sub_del = client.delete(f"/api/subjects/{subject['id']}")
    assert sub_del.status_code == 204
