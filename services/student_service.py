import re
from db import get_db_cursor

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def list_students(config, q=None):
    """List all students, optionally filtered by search query q."""
    search = str(q).strip() if q else ""
    with get_db_cursor(config_class=config) as cursor:
        if search:
            if search.isdigit():
                cursor.execute(
                    """
                    SELECT * FROM students
                    WHERE id = %s OR roll_no = %s OR student_name LIKE %s
                    ORDER BY id ASC;
                    """,
                    (int(search), search, f"%{search}%")
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM students
                    WHERE roll_no = %s OR student_name LIKE %s
                    ORDER BY id ASC;
                    """,
                    (search, f"%{search}%")
                )
        else:
            cursor.execute("SELECT * FROM students ORDER BY id ASC;")
        return cursor.fetchall()


def get_student_by_id(config, student_id):
    """Retrieve a student by primary key ID."""
    with get_db_cursor(config_class=config) as cursor:
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        return cursor.fetchone()


def create_student(config, data):
    """
    Validate and create a new student.
    Returns: (student_dict, None, 201) on success,
             (None, error_msg, status_code) on failure.
    """
    if data is None:
        return None, "No JSON body received", 400

    required_fields = [
        "roll_no", "student_name", "email",
        "department", "course", "academic_year", "semester"
    ]
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            return None, f"'{field}' is required", 400

    email = str(data["email"]).strip()
    if not EMAIL_REGEX.match(email):
        return None, "Invalid email format", 400

    try:
        semester = int(data["semester"])
        if semester < 1 or semester > 12:
            return None, "Semester must be an integer between 1 and 12", 400
    except (ValueError, TypeError):
        return None, "Semester must be a valid integer", 400

    roll_no = str(data["roll_no"]).strip()
    student_name = str(data["student_name"]).strip()
    department = str(data["department"]).strip()
    course = str(data["course"]).strip()
    academic_year = str(data["academic_year"]).strip()

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute(
            "SELECT id, roll_no, email FROM students WHERE roll_no = %s OR email = %s;",
            (roll_no, email)
        )
        existing = cursor.fetchone()
        if existing:
            if existing["roll_no"] == roll_no:
                return None, f"Student with roll number '{roll_no}' already exists", 409
            if existing["email"] == email:
                return None, f"Student with email '{email}' already exists", 409

        cursor.execute(
            """
            INSERT INTO students (roll_no, student_name, email, department, course, academic_year, semester)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (roll_no, student_name, email, department, course, academic_year, semester)
        )
        student_id = cursor.lastrowid
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        student = cursor.fetchone()
        return student, None, 201


def update_student(config, student_id, data):
    """
    Validate and partially update a student.
    Returns: (updated_student, None, 200) on success,
             (None, error_msg, status_code) on failure.
    """
    if data is None:
        return None, "No JSON body received", 400

    allowed_fields = [
        "roll_no", "student_name", "email",
        "department", "course", "academic_year", "semester"
    ]
    updates = {}
    for f in allowed_fields:
        if f in data:
            updates[f] = data[f]

    if not updates:
        return None, "No valid fields provided for update", 400

    if "email" in updates:
        email = str(updates["email"]).strip()
        if not EMAIL_REGEX.match(email):
            return None, "Invalid email format", 400
        updates["email"] = email

    if "semester" in updates:
        try:
            sem = int(updates["semester"])
            if sem < 1 or sem > 12:
                return None, "Semester must be an integer between 1 and 12", 400
            updates["semester"] = sem
        except (ValueError, TypeError):
            return None, "Semester must be a valid integer", 400

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        student = cursor.fetchone()
        if not student:
            return None, f"Student with ID {student_id} not found", 404

        if "roll_no" in updates and updates["roll_no"] != student["roll_no"]:
            cursor.execute(
                "SELECT id FROM students WHERE roll_no = %s AND id != %s;",
                (updates["roll_no"], student_id)
            )
            if cursor.fetchone():
                return None, f"Roll number '{updates['roll_no']}' is already in use", 409

        if "email" in updates and updates["email"] != student["email"]:
            cursor.execute(
                "SELECT id FROM students WHERE email = %s AND id != %s;",
                (updates["email"], student_id)
            )
            if cursor.fetchone():
                return None, f"Email '{updates['email']}' is already in use", 409

        set_clauses = [f"{k} = %s" for k in updates.keys()]
        values = list(updates.values())
        values.append(student_id)

        sql = f"UPDATE students SET {', '.join(set_clauses)} WHERE id = %s;"
        cursor.execute(sql, tuple(values))

        cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
        updated_student = cursor.fetchone()
        return updated_student, None, 200


def delete_student(config, student_id):
    """
    Delete a student by primary key ID.
    Returns: (True, None, 204) on success,
             (False, error_msg, 404) if not found.
    """
    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT id FROM students WHERE id = %s;", (student_id,))
        if not cursor.fetchone():
            return False, f"Student with ID {student_id} not found", 404

        cursor.execute("DELETE FROM students WHERE id = %s;", (student_id,))
        return True, None, 204
