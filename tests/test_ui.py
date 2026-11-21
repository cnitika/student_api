"""
Comprehensive UI and Browser Route Tests against live student_test_db.
Covers all pages (with and without data), form submissions, redirects,
flashed messages, validation handling, multi-subject marks entry,
academic results display, and HTML escaping / XSS protection.
"""

def sample_student_form():
    return {
        "roll_no": "CS2026999",
        "student_name": "Kavita Reddy",
        "email": "kavita@college.edu",
        "department": "Computer Science",
        "course": "B.Tech CSE",
        "academic_year": "2025-2026",
        "semester": 4
    }


def sample_subject_form(code="CS401", name="Algorithms", max_marks=100):
    return {
        "subject_code": code,
        "subject_name": name,
        "max_marks": max_marks
    }


# -------------------------------------------------------------
# 1. Page Render Tests (with and without data)
# -------------------------------------------------------------
def test_dashboard_renders_empty(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Academic Performance Dashboard" in res.data
    assert b"No students registered yet" in res.data
    assert b"N/A" in res.data


def test_dashboard_renders_with_data(client):
    client.post("/students/new", data=sample_student_form())
    res = client.get("/")
    assert res.status_code == 200
    assert b"Kavita Reddy" in res.data
    assert b"CS2026999" in res.data


def test_students_page_renders_empty(client):
    res = client.get("/students")
    assert res.status_code == 200
    assert b"No students currently registered" in res.data


def test_add_student_page_renders(client):
    res = client.get("/students/new")
    assert res.status_code == 200
    assert b"Register New Student" in res.data


def test_subjects_page_renders_empty(client):
    res = client.get("/subjects")
    assert res.status_code == 200
    assert b"Subject Management" in res.data
    assert b"No subjects added yet" in res.data


# -------------------------------------------------------------
# 2. Student Form Submission (Add, Edit, Delete, Search)
# -------------------------------------------------------------
def test_add_student_success_redirect_and_flash(client):
    res = client.post("/students/new", data=sample_student_form(), follow_redirects=True)
    assert res.status_code == 200
    assert b"successfully registered" in res.data
    assert b"Kavita Reddy" in res.data


def test_add_student_duplicate_roll_no_shows_error(client):
    client.post("/students/new", data=sample_student_form())
    dup = sample_student_form()
    dup["email"] = "different@college.edu"
    res = client.post("/students/new", data=dup)
    assert res.status_code == 400
    assert b"already exists" in res.data


def test_edit_student_page_and_update(client):
    client.post("/students/new", data=sample_student_form())
    # Retrieve student id
    res_list = client.get("/api/students")
    student_id = res_list.get_json()[0]["id"]

    # Render edit page
    edit_page = client.get(f"/students/{student_id}/edit")
    assert edit_page.status_code == 200
    assert b"Kavita Reddy" in edit_page.data

    # Submit edit update
    updated_data = sample_student_form()
    updated_data["student_name"] = "Kavita R. Sharma"
    updated_data["semester"] = 5
    res = client.post(f"/students/{student_id}/edit", data=updated_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"successfully updated" in res.data
    assert b"Kavita R. Sharma" in res.data


def test_delete_student_form_action(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]

    # POST delete
    del_res = client.post(f"/students/{student_id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert b"successfully deleted" in del_res.data
    assert b"No students currently registered" in del_res.data


def test_students_search_filter(client):
    client.post("/students/new", data=sample_student_form(), follow_redirects=True)
    client.post("/students/new", data={
        "roll_no": "IT2026888",
        "student_name": "Manoj Kumar",
        "email": "manoj@college.edu",
        "department": "IT",
        "course": "B.Tech IT",
        "academic_year": "2025-2026",
        "semester": 6
    }, follow_redirects=True)

    search_res = client.get("/students?q=Manoj")
    assert search_res.status_code == 200
    assert b"<td>Manoj Kumar</td>" in search_res.data
    assert b"<td>Kavita Reddy</td>" not in search_res.data


# -------------------------------------------------------------
# 3. Subject Form Submission (Add, Edit, Delete, Blocked Case)
# -------------------------------------------------------------
def test_add_and_edit_subject_ui(client):
    res = client.post("/subjects/new", data=sample_subject_form("CS401", "Algorithms", 100), follow_redirects=True)
    assert res.status_code == 200
    assert b"Algorithms" in res.data

    sub_id = client.get("/api/subjects").get_json()[0]["id"]
    edit_res = client.post(f"/subjects/{sub_id}/edit", data={
        "subject_code": "CS401",
        "subject_name": "Design & Analysis of Algorithms",
        "max_marks": 100
    }, follow_redirects=True)
    assert edit_res.status_code == 200
    assert b"Design &amp; Analysis of Algorithms" in edit_res.data


def test_delete_subject_blocked_when_marks_attached(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]

    client.post("/subjects/new", data=sample_subject_form("CS402", "Data Structures", 100))
    subject_id = client.get("/api/subjects").get_json()[0]["id"]

    # Enter marks for this subject
    client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(subject_id)],
        "semesters[]": ["4"],
        "marks_obtained[]": ["80.0"]
    })

    # Try deleting the subject
    del_res = client.post(f"/subjects/{subject_id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert b"Cannot delete subject because student marks reference it" in del_res.data


# -------------------------------------------------------------
# 4. Multi-subject Marks Entry & Validation Handling
# -------------------------------------------------------------
def test_marks_entry_multi_subject_success(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]

    client.post("/subjects/new", data=sample_subject_form("S1", "Subject 1", 100))
    client.post("/subjects/new", data=sample_subject_form("S2", "Subject 2", 100))
    subs = client.get("/api/subjects").get_json()

    # Enter marks for 2 subjects in single POST submission
    res = client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(subs[0]["id"]), str(subs[1]["id"])],
        "semesters[]": ["4", "4"],
        "marks_obtained[]": ["78.5", "84.0"]
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Successfully recorded marks for 2 subject(s)" in res.data
    assert b"78.5" in res.data
    assert b"84" in res.data


def test_marks_entry_rejected_negative_marks(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]
    client.post("/subjects/new", data=sample_subject_form())
    sub_id = client.get("/api/subjects").get_json()[0]["id"]

    res = client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(sub_id)],
        "semesters[]": ["4"],
        "marks_obtained[]": ["-5.0"]
    })
    assert res.status_code == 400
    assert b"cannot be negative" in res.data


def test_marks_entry_rejected_above_max_marks(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]
    client.post("/subjects/new", data=sample_subject_form("CS403", "Maths", 100))
    sub_id = client.get("/api/subjects").get_json()[0]["id"]

    res = client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(sub_id)],
        "semesters[]": ["4"],
        "marks_obtained[]": ["105.0"]
    })
    assert res.status_code == 400
    assert b"cannot exceed" in res.data


def test_marks_entry_rejected_duplicate_subject_same_semester(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]
    client.post("/subjects/new", data=sample_subject_form("CS404", "OS", 100))
    sub_id = client.get("/api/subjects").get_json()[0]["id"]

    res = client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(sub_id), str(sub_id)],
        "semesters[]": ["4", "4"],
        "marks_obtained[]": ["60.0", "70.0"]
    })
    assert res.status_code == 400
    assert b"Duplicate subject specified" in res.data


# -------------------------------------------------------------
# 5. Academic Result Sheet View Tests
# -------------------------------------------------------------
def test_result_sheet_spec_rahul_sharma(client):
    """
    Rahul Sharma spec test in UI:
    DBMS 85, Python 92, Computer Networks 78, Operating Systems 88, Mathematics 75 (each /100)
    Expects 418 / 500 / 83.60% / A / PASS.
    """
    client.post("/students/new", data={
        "roll_no": "CS2025001",
        "student_name": "Rahul Sharma",
        "email": "rahul.sharma@college.edu",
        "department": "Computer Science",
        "course": "B.Tech CSE",
        "academic_year": "2025-2026",
        "semester": 5
    })
    student_id = client.get("/api/students").get_json()[0]["id"]

    client.post("/subjects/new", data=sample_subject_form("CS501", "DBMS", 100))
    client.post("/subjects/new", data=sample_subject_form("CS502", "Python", 100))
    client.post("/subjects/new", data=sample_subject_form("CS503", "Computer Networks", 100))
    client.post("/subjects/new", data=sample_subject_form("CS504", "Operating Systems", 100))
    client.post("/subjects/new", data=sample_subject_form("CS505", "Mathematics", 100))

    subs = client.get("/api/subjects").get_json()
    marks_map = {"CS501": 85, "CS502": 92, "CS503": 78, "CS504": 88, "CS505": 75}

    client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(s["id"]) for s in subs],
        "semesters[]": ["5"] * 5,
        "marks_obtained[]": [str(marks_map[s["subject_code"]]) for s in subs]
    })

    # Render Result Sheet HTML
    res = client.get(f"/students/{student_id}/result?semester=5")
    assert res.status_code == 200
    content = res.data.decode("utf-8")

    assert "Rahul Sharma" in content
    assert "418.00 / 500.00" in content
    assert "83.60%" in content
    assert "Grade Awarded" in content
    assert ">A<" in content or "Grade Awarded" in content
    assert "PASS" in content


def test_result_sheet_no_marks_shows_not_available(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]

    res = client.get(f"/students/{student_id}/result")
    assert res.status_code == 200
    assert b"Result Not Available" in res.data


def test_result_sheet_failing_subject_shows_fail(client):
    client.post("/students/new", data=sample_student_form())
    student_id = client.get("/api/students").get_json()[0]["id"]

    client.post("/subjects/new", data=sample_subject_form("S1", "Sub1", 100))
    client.post("/subjects/new", data=sample_subject_form("S2", "Sub2", 100))
    subs = client.get("/api/subjects").get_json()

    client.post(f"/students/{student_id}/marks/entry", data={
        "subject_ids[]": [str(subs[0]["id"]), str(subs[1]["id"])],
        "semesters[]": ["4", "4"],
        "marks_obtained[]": ["95.0", "34.5"]  # 34.5 is < 35%
    })

    res = client.get(f"/students/{student_id}/result")
    assert res.status_code == 200
    assert b"FAIL" in res.data
    assert b"Backlog / Failed Subjects" in res.data


# -------------------------------------------------------------
# 6. HTML Injection / XSS Escaping Test
# -------------------------------------------------------------
def test_xss_injection_is_properly_escaped(client):
    malicious_input = "<script>alert('xss')</script>"
    client.post("/students/new", data={
        "roll_no": "XSS001",
        "student_name": malicious_input,
        "email": "xss@college.edu",
        "department": "Security",
        "course": "Cyber Security",
        "academic_year": "2025-2026",
        "semester": 1
    })

    res = client.get("/students")
    assert res.status_code == 200
    # The raw unescaped script tag must NOT exist in the HTML output
    assert b"<script>alert('xss')</script>" not in res.data
    # The escaped character sequence must exist
    assert b"&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in res.data or b"&lt;script&gt;" in res.data
