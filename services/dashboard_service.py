from decimal import Decimal
from db import get_db_cursor
from services.results import calculate_academic_result


def get_dashboard_stats(config):
    """
    Calculate real statistics for the academic dashboard.
    Returns:
    - total_students (int)
    - total_subjects (int)
    - students_with_results (int)
    - pass_count (int)
    - fail_count (int)
    - average_percentage (float or None)
    - recent_students (list of dicts)
    """
    with get_db_cursor(config_class=config) as cursor:
        # Total students
        cursor.execute("SELECT COUNT(*) as cnt FROM students;")
        total_students = cursor.fetchone()["cnt"]

        # Total subjects
        cursor.execute("SELECT COUNT(*) as cnt FROM subjects;")
        total_subjects = cursor.fetchone()["cnt"]

        # Recent students
        cursor.execute("SELECT * FROM students ORDER BY id DESC LIMIT 5;")
        recent_students = cursor.fetchall()

        # Fetch all students to evaluate their active semester academic result
        cursor.execute("SELECT * FROM students ORDER BY id ASC;")
        all_students = cursor.fetchall()

        pass_thresh = config.get("PASS_THRESHOLD_PERCENT", Decimal("35.00")) if hasattr(config, "get") else getattr(config, "PASS_THRESHOLD_PERCENT", Decimal("35.00"))
        scale = config.get("GRADE_SCALE") if hasattr(config, "get") else getattr(config, "GRADE_SCALE", None)

        students_with_results = 0
        pass_count = 0
        fail_count = 0
        percentages = []

        for st in all_students:
            s_id = st["id"]
            sem = st["semester"]

            cursor.execute(
                """
                SELECT s.subject_code, s.subject_name, s.max_marks, m.marks_obtained
                FROM marks m
                JOIN subjects s ON m.subject_id = s.id
                WHERE m.student_id = %s AND m.semester = %s;
                """,
                (s_id, sem)
            )
            marks_rows = cursor.fetchall()
            if marks_rows:
                res = calculate_academic_result(
                    student_info=st,
                    marks_records=marks_rows,
                    pass_threshold=pass_thresh,
                    grade_scale=scale,
                    semester=sem
                )
                if res["status"] in ("PASS", "FAIL"):
                    students_with_results += 1
                    if res["status"] == "PASS":
                        pass_count += 1
                    else:
                        fail_count += 1
                    if res["percentage"] is not None:
                        percentages.append(res["percentage"])

        avg_percentage = round(sum(percentages) / len(percentages), 2) if percentages else None

        return {
            "total_students": total_students,
            "total_subjects": total_subjects,
            "students_with_results": students_with_results,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "average_percentage": avg_percentage,
            "recent_students": recent_students
        }
