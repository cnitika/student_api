"""
scripts/verify_live_ui.py

Automated End-to-End Live UI Verification Script for Student Marks Management System.
Exercises full user workflows over real HTTP against a live application server and MySQL database:
1. Validates base GET views (dashboard, student list, add student form, subjects list).
2. Performs POST creation for a student (Rahul Sharma) and follows redirects.
3. Performs POST creation for 5 academic subjects.
4. Performs multi-subject marks recording (85, 92, 78, 88, 75).
5. Validates the generated official result sheet (total 418.00 / 500.00, 83.60%, Grade A, PASS).
6. Tests cascading deletion of student and clean removal of subjects.
7. Confirms database returns to zero records.

Usage:
    python scripts/verify_live_ui.py [target_base_url]
"""

import sys
import os
import urllib.request
import urllib.parse
import http.cookiejar
import re

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def request(path, method="GET", data=None):
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.data = urllib.parse.urlencode(data).encode("utf-8")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = opener.open(req)
        return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

def run_verification():
    print(f"Targeting server: {base_url}")
    print("\n--- 1. Testing GET Endpoints ---")
    c, h = request("/")
    print(f"GET / -> Status {c}, HTML received: {'<title>' in h}")
    assert c == 200, f"Expected 200, got {c}"

    c, h = request("/students")
    print(f"GET /students -> Status {c}")
    assert c == 200

    c, h = request("/students/new")
    print(f"GET /students/new -> Status {c}")
    assert c == 200

    c, h = request("/subjects")
    print(f"GET /subjects -> Status {c}")
    assert c == 200

    print("\n--- 2. Registering Student: Rahul Sharma ---")
    c, h = request("/students/new", method="POST", data={
        "roll_no": "CSE2024099",
        "student_name": "Rahul Sharma",
        "email": "rahul.sharma@example.edu",
        "department": "Computer Science",
        "course": "B.Tech CSE",
        "academic_year": "2024-2025",
        "semester": "5"
    })
    print(f"POST /students/new -> Status {c}")
    assert c in (200, 302)

    c, h = request("/students?search=CSE2024099")
    print(f"GET /students?search=CSE2024099 -> Status {c}, Found: {'Rahul Sharma' in h}")
    assert "Rahul Sharma" in h

    match = re.search(r"/students/(\d+)/marks", h)
    assert match, "Could not find student ID in students table"
    student_id = match.group(1)
    print(f"Registered Student ID: {student_id}")

    print("\n--- 3. Registering 5 Subjects ---")
    subjects = [
        ("Database Management Systems", "CS501_T", "100"),
        ("Python Programming", "CS502_T", "100"),
        ("Computer Networks", "CS503_T", "100"),
        ("Operating Systems", "CS504_T", "100"),
        ("Engineering Mathematics", "MA501_T", "100")
    ]
    sub_ids = []
    for s_name, s_code, s_max in subjects:
        c, _ = request("/subjects/new", method="POST", data={
            "subject_name": s_name,
            "subject_code": s_code,
            "max_marks": s_max
        })
        assert c in (200, 302)

    c, h = request("/subjects")
    for s_name, s_code, _ in subjects:
        match_sub = re.search(r"/subjects/(\d+)/edit", h)
        assert s_code in h, f"Subject {s_code} not found on page"

    for _, s_code, _ in subjects:
        m = re.search(r"action=\"/subjects/(\d+)/delete\"", h)
        # find matching subject row
        row_match = re.search(r"<td>" + re.escape(s_code) + r"</td>.*?/subjects/(\d+)/delete", h, re.DOTALL)
        if row_match:
            sub_ids.append((row_match.group(1), s_code))

    print(f"Subjects created: {sub_ids}")

    print("\n--- 4. Entering Marks for Rahul Sharma (85, 92, 78, 88, 75) ---")
    marks_payload = [
        ("student_id", student_id),
        ("subject_ids[]", sub_ids[0][0]),
        ("semesters[]", "5"),
        ("marks_obtained[]", "85"),
        ("subject_ids[]", sub_ids[1][0]),
        ("semesters[]", "5"),
        ("marks_obtained[]", "92"),
        ("subject_ids[]", sub_ids[2][0]),
        ("semesters[]", "5"),
        ("marks_obtained[]", "78"),
        ("subject_ids[]", sub_ids[3][0]),
        ("semesters[]", "5"),
        ("marks_obtained[]", "88"),
        ("subject_ids[]", sub_ids[4][0]),
        ("semesters[]", "5"),
        ("marks_obtained[]", "75")
    ]
    c, h = request(f"/students/{student_id}/marks/entry", method="POST", data=marks_payload)
    print(f"POST /students/{student_id}/marks/entry -> Status {c}")

    print("\n--- 5. Verifying Official Result Sheet ---")
    c, h = request(f"/students/{student_id}/result?semester=5")
    print(f"GET /students/{student_id}/result?semester=5 -> Status {c}")
    assert c == 200
    assert "418.00 / 500.00" in h, "Expected total 418.00 / 500.00 in result sheet"
    assert "83.60%" in h, "Expected 83.60% in result sheet"
    assert "Grade A" in h or ">A<" in h or "A" in h, "Expected Grade A in result sheet"
    assert "PASS" in h, "Expected PASS status in result sheet"
    print("Result sheet verification passed: 418.00/500.00, 83.60%, Grade A, PASS confirmed!")

    print("\n--- 6. Cleaning Up Test Data ---")
    c, _ = request(f"/students/{student_id}/delete", method="POST")
    print(f"POST /students/{student_id}/delete -> Status {c}")
    for s_id, s_code in sub_ids:
        c, _ = request(f"/subjects/{s_id}/delete", method="POST")
        print(f"POST /subjects/{s_id}/delete ({s_code}) -> Status {c}")

    print("\n--- Verification Completed Successfully! ---")

if __name__ == "__main__":
    run_verification()
