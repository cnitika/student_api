from decimal import Decimal
import pytest
from services.results import (
    calculate_grade,
    calculate_academic_result,
    DEFAULT_PASS_THRESHOLD,
    DEFAULT_GRADE_SCALE
)


def test_grade_boundaries():
    assert calculate_grade(Decimal("90.00")) == "A+"
    assert calculate_grade(Decimal("95.50")) == "A+"
    assert calculate_grade(Decimal("89.99")) == "A"
    assert calculate_grade(Decimal("80.00")) == "A"
    assert calculate_grade(Decimal("79.99")) == "B"
    assert calculate_grade(Decimal("70.00")) == "B"
    assert calculate_grade(Decimal("69.99")) == "C"
    assert calculate_grade(Decimal("60.00")) == "C"
    assert calculate_grade(Decimal("59.99")) == "D"
    assert calculate_grade(Decimal("50.00")) == "D"
    assert calculate_grade(Decimal("49.99")) == "F"
    assert calculate_grade(Decimal("0.00")) == "F"


def test_rounding_edge_cases():
    student = {"id": 1, "student_name": "Test Student"}

    # Case 1: 89.995% rounds up to 90.00% (A+)
    # 179.99 / 200 = 89.995%
    records = [
        {"subject_code": "S1", "subject_name": "Sub 1", "max_marks": 100, "marks_obtained": Decimal("90.00")},
        {"subject_code": "S2", "subject_name": "Sub 2", "max_marks": 100, "marks_obtained": Decimal("89.995")},
    ]
    res = calculate_academic_result(student, records, semester=1)
    assert res["percentage"] == 90.00
    assert res["grade"] == "A+"
    assert res["status"] == "PASS"

    # Case 2: 89.994% rounds down to 89.99% (A)
    # 179.988 / 200 = 89.994%
    records = [
        {"subject_code": "S1", "subject_name": "Sub 1", "max_marks": 100, "marks_obtained": Decimal("90.00")},
        {"subject_code": "S2", "subject_name": "Sub 2", "max_marks": 100, "marks_obtained": Decimal("89.988")},
    ]
    res = calculate_academic_result(student, records, semester=1)
    assert res["percentage"] == 89.99
    assert res["grade"] == "A"


def test_subject_pass_rule_boundary_35_percent():
    student = {"id": 1, "student_name": "Borderline Student"}

    # Exactly 35.00 out of 100 -> PASS
    records_pass = [
        {"subject_code": "S1", "subject_name": "Sub 1", "max_marks": 100, "marks_obtained": 35.00},
        {"subject_code": "S2", "subject_name": "Sub 2", "max_marks": 100, "marks_obtained": 80.00},
    ]
    res_pass = calculate_academic_result(student, records_pass, semester=1)
    assert res_pass["status"] == "PASS"
    assert len(res_pass["failed_subjects"]) == 0

    # 34.99 out of 100 -> FAIL even if overall percentage is high
    records_fail = [
        {"subject_code": "S1", "subject_name": "Sub 1", "max_marks": 100, "marks_obtained": 34.99},
        {"subject_code": "S2", "subject_name": "Sub 2", "max_marks": 100, "marks_obtained": 95.00},
    ]
    res_fail = calculate_academic_result(student, records_fail, semester=1)
    # Overall percentage is (129.99 / 200) * 100 = 65.00%
    assert res_fail["percentage"] == 65.00
    assert res_fail["grade"] == "C"
    assert res_fail["status"] == "FAIL"
    assert len(res_fail["failed_subjects"]) == 1
    assert res_fail["failed_subjects"][0]["subject_code"] == "S1"


def test_no_marks_case():
    student = {"id": 1, "student_name": "New Student"}
    res = calculate_academic_result(student, [], semester=2)
    assert res["status"] == "Result Not Available"
    assert res["total_obtained"] is None
    assert res["total_max"] is None
    assert res["percentage"] is None
    assert res["grade"] is None
    assert res["failed_subjects"] == []


def test_spec_rahul_sharma_calculation():
    """
    Spec requirement:
    Rahul Sharma with 5 subjects:
    DBMS 85/100, Python 92/100, Computer Networks 78/100, Operating Systems 88/100, Mathematics 75/100
    Total: 418/500, 83.60%, Grade: A, Status: PASS
    """
    student = {
        "id": 1,
        "roll_no": "CS2026001",
        "student_name": "Rahul Sharma",
        "department": "Computer Science",
        "course": "B.Tech CSE",
        "academic_year": "2025-2026",
        "semester": 5
    }
    records = [
        {"subject_code": "CS501", "subject_name": "Database Management Systems", "max_marks": 100, "marks_obtained": 85},
        {"subject_code": "CS502", "subject_name": "Python Programming", "max_marks": 100, "marks_obtained": 92},
        {"subject_code": "CS503", "subject_name": "Computer Networks", "max_marks": 100, "marks_obtained": 78},
        {"subject_code": "CS504", "subject_name": "Operating Systems", "max_marks": 100, "marks_obtained": 88},
        {"subject_code": "CS505", "subject_name": "Mathematics", "max_marks": 100, "marks_obtained": 75},
    ]

    res = calculate_academic_result(student, records, semester=5)
    assert res["total_obtained"] == 418.0
    assert res["total_max"] == 500.0
    assert res["percentage"] == 83.60
    assert res["grade"] == "A"
    assert res["status"] == "PASS"
    assert len(res["failed_subjects"]) == 0
