from decimal import Decimal, ROUND_HALF_UP

DEFAULT_PASS_THRESHOLD = Decimal("35.00")

DEFAULT_GRADE_SCALE = [
    (Decimal("90.00"), "A+"),
    (Decimal("80.00"), "A"),
    (Decimal("70.00"), "B"),
    (Decimal("60.00"), "C"),
    (Decimal("50.00"), "D"),
]


def calculate_grade(percentage: Decimal, grade_scale=None) -> str:
    """Determine grade based on percentage using the grade scale."""
    scale = grade_scale if grade_scale is not None else DEFAULT_GRADE_SCALE
    for min_pct, grade in scale:
        if percentage >= min_pct:
            return grade
    return "F"


def calculate_academic_result(
    student_info: dict,
    marks_records: list,
    pass_threshold: Decimal = DEFAULT_PASS_THRESHOLD,
    grade_scale=None,
    semester: int = None
) -> dict:
    """
    Calculate the academic result for a student in a semester.
    Pure function with no database or framework dependencies.

    marks_records is expected to be a list of dictionaries with:
    - subject_name (str)
    - subject_code (str)
    - max_marks (Decimal, int, or float)
    - marks_obtained (Decimal, int, or float)
    """
    if not marks_records:
        return {
            "student": student_info,
            "semester": semester,
            "subjects": [],
            "total_obtained": None,
            "total_max": None,
            "percentage": None,
            "grade": None,
            "status": "Result Not Available",
            "failed_subjects": []
        }

    total_obtained = Decimal("0.00")
    total_max = Decimal("0.00")
    subject_rows = []
    failed_subjects = []

    for rec in marks_records:
        obtained = Decimal(str(rec["marks_obtained"]))
        max_marks = Decimal(str(rec["max_marks"]))

        total_obtained += obtained
        total_max += max_marks

        # Subject percentage rounded half up
        sub_pct = ((obtained / max_marks) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Subject pass rule: marks_obtained >= 35% of that subject's max_marks
        required_marks = (max_marks * pass_threshold / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        passed = obtained >= required_marks

        if not passed:
            failed_subjects.append({
                "subject_code": rec.get("subject_code"),
                "subject_name": rec.get("subject_name"),
                "marks_obtained": float(obtained),
                "max_marks": float(max_marks),
                "required_marks": float(required_marks)
            })

        subject_rows.append({
            "subject_code": rec.get("subject_code"),
            "subject_name": rec.get("subject_name"),
            "max_marks": float(max_marks),
            "marks_obtained": float(obtained),
            "percentage": float(sub_pct),
            "status": "PASS" if passed else "FAIL"
        })

    if total_max > Decimal("0.00"):
        raw_percentage = (total_obtained / total_max) * Decimal("100")
        percentage = raw_percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        percentage = Decimal("0.00")

    grade = calculate_grade(percentage, grade_scale=grade_scale)
    overall_status = "PASS" if len(failed_subjects) == 0 else "FAIL"

    return {
        "student": student_info,
        "semester": semester,
        "subjects": subject_rows,
        "total_obtained": float(total_obtained),
        "total_max": float(total_max),
        "percentage": float(percentage),
        "grade": grade,
        "status": overall_status,
        "failed_subjects": failed_subjects
    }
