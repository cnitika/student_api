from decimal import Decimal
from db import get_db_cursor
from services.results import calculate_academic_result


def get_student_marks(config, student_id, semester=None):
    """
    Get all marks for a student, optionally filtered by semester.
    Returns: (marks_list, None, 200) or (None, error_msg, 404)
    """
    with get_db_cursor(config_class=config) as cursor:
        cursor.execute("SELECT id FROM students WHERE id = %s;", (student_id,))
        if not cursor.fetchone():
            return None, f"Student with ID {student_id} not found", 404

        if semester is not None:
            cursor.execute(
                """
                SELECT m.id, m.student_id, m.subject_id, m.semester, m.marks_obtained,
                       s.subject_code, s.subject_name, s.max_marks, m.created_at, m.updated_at
                FROM marks m
                JOIN subjects s ON m.subject_id = s.id
                WHERE m.student_id = %s AND m.semester = %s
                ORDER BY s.subject_code ASC;
                """,
                (student_id, int(semester))
            )
        else:
            cursor.execute(
                """
                SELECT m.id, m.student_id, m.subject_id, m.semester, m.marks_obtained,
                       s.subject_code, s.subject_name, s.max_marks, m.created_at, m.updated_at
                FROM marks m
                JOIN subjects s ON m.subject_id = s.id
                WHERE m.student_id = %s
                ORDER BY m.semester ASC, s.subject_code ASC;
                """,
                (student_id,)
            )
        marks = cursor.fetchall()
        for m in marks:
            if "marks_obtained" in m and m["marks_obtained"] is not None:
                m["marks_obtained"] = float(m["marks_obtained"])
            if "max_marks" in m and m["max_marks"] is not None:
                m["max_marks"] = float(m["max_marks"])
        return marks, None, 200


def add_student_mark(config, student_id, data):
    """
    Validate and add a mark record for a student.
    Returns: (created_mark, None, 201) or (None, error_msg, status_code)
    """
    if data is None:
        return None, "No JSON body received", 400

    if "subject_id" not in data or data["subject_id"] is None or str(data["subject_id"]).strip() == "":
        return None, "'subject_id' is required", 400
    if "marks_obtained" not in data or data["marks_obtained"] is None or str(data["marks_obtained"]).strip() == "":
        return None, "'marks_obtained' is required", 400

    try:
        subject_id = int(data["subject_id"])
    except (ValueError, TypeError):
        return None, "'subject_id' must be an integer", 400

    try:
        marks_obtained = Decimal(str(data["marks_obtained"]))
        if marks_obtained < Decimal("0"):
            return None, "marks_obtained cannot be negative", 400
    except Exception:
        return None, "marks_obtained must be a valid numeric value", 400

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT id, semester FROM students WHERE id = %s;", (student_id,))
        student = cursor.fetchone()
        if not student:
            return None, f"Student with ID {student_id} not found", 404

        if "semester" in data and data["semester"] is not None and str(data["semester"]).strip() != "":
            try:
                semester = int(data["semester"])
                if semester < 1 or semester > 12:
                    return None, "Semester must be between 1 and 12", 400
            except (ValueError, TypeError):
                return None, "Semester must be a valid integer", 400
        else:
            semester = student["semester"]

        cursor.execute("SELECT id, subject_code, subject_name, max_marks FROM subjects WHERE id = %s;", (subject_id,))
        subject = cursor.fetchone()
        if not subject:
            return None, f"Subject with ID {subject_id} not found", 404

        max_marks = Decimal(str(subject["max_marks"]))
        if marks_obtained > max_marks:
            return None, f"Marks obtained ({marks_obtained}) cannot exceed subject maximum marks ({max_marks})", 400

        cursor.execute(
            """
            SELECT id FROM marks
            WHERE student_id = %s AND subject_id = %s AND semester = %s;
            """,
            (student_id, subject_id, semester)
        )
        if cursor.fetchone():
            return None, f"Marks already exist for subject '{subject['subject_code']}' in semester {semester}", 409

        cursor.execute(
            """
            INSERT INTO marks (student_id, subject_id, semester, marks_obtained)
            VALUES (%s, %s, %s, %s);
            """,
            (student_id, subject_id, semester, float(marks_obtained))
        )
        mark_id = cursor.lastrowid

        cursor.execute(
            """
            SELECT m.id, m.student_id, m.subject_id, m.semester, m.marks_obtained,
                   s.subject_code, s.subject_name, s.max_marks, m.created_at
            FROM marks m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.id = %s;
            """,
            (mark_id,)
        )
        created_mark = cursor.fetchone()
        if created_mark:
            created_mark["marks_obtained"] = float(created_mark["marks_obtained"])
            created_mark["max_marks"] = float(created_mark["max_marks"])
        return created_mark, None, 201


def update_mark(config, mark_id, data):
    """
    Update marks_obtained for an existing mark record.
    Returns: (updated_mark, None, 200) or (None, error_msg, status_code)
    """
    if data is None or "marks_obtained" not in data or data["marks_obtained"] is None or str(data["marks_obtained"]).strip() == "":
        return None, "'marks_obtained' is required in body", 400

    try:
        new_marks = Decimal(str(data["marks_obtained"]))
        if new_marks < Decimal("0"):
            return None, "marks_obtained cannot be negative", 400
    except Exception:
        return None, "marks_obtained must be a valid numeric value", 400

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute(
            """
            SELECT m.id, m.marks_obtained, s.max_marks
            FROM marks m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.id = %s;
            """,
            (mark_id,)
        )
        mark = cursor.fetchone()
        if not mark:
            return None, f"Mark record with ID {mark_id} not found", 404

        max_marks = Decimal(str(mark["max_marks"]))
        if new_marks > max_marks:
            return None, f"Marks obtained ({new_marks}) cannot exceed maximum marks ({max_marks})", 400

        cursor.execute(
            "UPDATE marks SET marks_obtained = %s WHERE id = %s;",
            (float(new_marks), mark_id)
        )

        cursor.execute(
            """
            SELECT m.id, m.student_id, m.subject_id, m.semester, m.marks_obtained,
                   s.subject_code, s.subject_name, s.max_marks, m.updated_at
            FROM marks m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.id = %s;
            """,
            (mark_id,)
        )
        updated = cursor.fetchone()
        if updated:
            updated["marks_obtained"] = float(updated["marks_obtained"])
            updated["max_marks"] = float(updated["max_marks"])
        return updated, None, 200


def delete_mark(config, mark_id):
    """Delete a mark record."""
    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT id FROM marks WHERE id = %s;", (mark_id,))
        if not cursor.fetchone():
            return False, f"Mark record with ID {mark_id} not found", 404

        cursor.execute("DELETE FROM marks WHERE id = %s;", (mark_id,))
        return True, None, 204


def get_student_academic_result(config, student_id, semester=None):
    """
    Calculate the academic result for a student in a semester.
    Returns: (result_dict, None, 200) or (None, error_msg, 404)
    """
    with get_db_cursor(config_class=config) as cursor:
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        student = cursor.fetchone()
        if not student:
            return None, f"Student with ID {student_id} not found", 404

        target_sem = int(semester) if semester is not None else student["semester"]

        cursor.execute(
            """
            SELECT s.subject_code, s.subject_name, s.max_marks, m.marks_obtained
            FROM marks m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.student_id = %s AND m.semester = %s
            ORDER BY s.subject_code ASC;
            """,
            (student_id, target_sem)
        )
        records = cursor.fetchall()

        pass_thresh = config.get("PASS_THRESHOLD_PERCENT", Decimal("35.00")) if hasattr(config, "get") else getattr(config, "PASS_THRESHOLD_PERCENT", Decimal("35.00"))
        scale = config.get("GRADE_SCALE") if hasattr(config, "get") else getattr(config, "GRADE_SCALE", None)

        result = calculate_academic_result(
            student_info=student,
            marks_records=records,
            pass_threshold=pass_thresh,
            grade_scale=scale,
            semester=target_sem
        )
        return result, None, 200
