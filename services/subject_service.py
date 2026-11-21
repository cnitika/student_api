from decimal import Decimal
from db import get_db_cursor


def list_subjects(config):
    """List all subjects with max_marks as float."""
    with get_db_cursor(config_class=config) as cursor:
        cursor.execute("SELECT * FROM subjects ORDER BY id ASC;")
        subjects = cursor.fetchall()
        for s in subjects:
            if "max_marks" in s and s["max_marks"] is not None:
                s["max_marks"] = float(s["max_marks"])
        return subjects


def get_subject_by_id(config, subject_id):
    """Retrieve subject by primary key ID."""
    with get_db_cursor(config_class=config) as cursor:
        cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
        sub = cursor.fetchone()
        if sub and "max_marks" in sub and sub["max_marks"] is not None:
            sub["max_marks"] = float(sub["max_marks"])
        return sub


def create_subject(config, data):
    """
    Validate and create a new subject.
    Returns: (subject_dict, None, 201) on success,
             (None, error_msg, status_code) on failure.
    """
    if data is None:
        return None, "No JSON body received", 400

    required = ["subject_code", "subject_name", "max_marks"]
    for f in required:
        if f not in data or data[f] is None or str(data[f]).strip() == "":
            return None, f"'{f}' is required", 400

    code = str(data["subject_code"]).strip()
    name = str(data["subject_name"]).strip()

    try:
        max_marks = Decimal(str(data["max_marks"]))
        if max_marks <= Decimal("0"):
            return None, "max_marks must be greater than 0", 400
    except Exception:
        return None, "max_marks must be a valid positive number", 400

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT id FROM subjects WHERE subject_code = %s;", (code,))
        if cursor.fetchone():
            return None, f"Subject code '{code}' already exists", 409

        cursor.execute(
            "INSERT INTO subjects (subject_code, subject_name, max_marks) VALUES (%s, %s, %s);",
            (code, name, float(max_marks))
        )
        sub_id = cursor.lastrowid
        cursor.execute("SELECT * FROM subjects WHERE id = %s;", (sub_id,))
        subject = cursor.fetchone()
        if subject and "max_marks" in subject and subject["max_marks"] is not None:
            subject["max_marks"] = float(subject["max_marks"])
        return subject, None, 201


def update_subject(config, subject_id, data):
    """
    Validate and partially update a subject.
    Returns: (updated_subject, None, 200) on success,
             (None, error_msg, status_code) on failure.
    """
    if data is None:
        return None, "No JSON body received", 400

    allowed = ["subject_code", "subject_name", "max_marks"]
    updates = {k: data[k] for k in allowed if k in data and data[k] is not None and str(data[k]).strip() != ""}
    if not updates:
        return None, "No valid fields provided for update", 400

    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
        subject = cursor.fetchone()
        if not subject:
            return None, f"Subject with ID {subject_id} not found", 404

        if "subject_code" in updates:
            new_code = str(updates["subject_code"]).strip()
            if new_code != subject["subject_code"]:
                cursor.execute(
                    "SELECT id FROM subjects WHERE subject_code = %s AND id != %s;",
                    (new_code, subject_id)
                )
                if cursor.fetchone():
                    return None, f"Subject code '{new_code}' already exists", 409
            updates["subject_code"] = new_code

        if "max_marks" in updates:
            try:
                new_max = Decimal(str(updates["max_marks"]))
                if new_max <= Decimal("0"):
                    return None, "max_marks must be greater than 0", 400
                cursor.execute("SELECT MAX(marks_obtained) as highest FROM marks WHERE subject_id = %s;", (subject_id,))
                highest = cursor.fetchone()["highest"]
                if highest is not None and Decimal(str(highest)) > new_max:
                    return None, f"Cannot set max_marks to {new_max} because existing marks obtained is {highest}", 400
                updates["max_marks"] = float(new_max)
            except Exception:
                return None, "max_marks must be a valid positive number", 400

        set_clauses = [f"{k} = %s" for k in updates.keys()]
        values = list(updates.values())
        values.append(subject_id)

        sql = f"UPDATE subjects SET {', '.join(set_clauses)} WHERE id = %s;"
        cursor.execute(sql, tuple(values))

        cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
        updated_sub = cursor.fetchone()
        if updated_sub and "max_marks" in updated_sub and updated_sub["max_marks"] is not None:
            updated_sub["max_marks"] = float(updated_sub["max_marks"])
        return updated_sub, None, 200


def delete_subject(config, subject_id):
    """
    Delete a subject if not referenced by marks records.
    Returns: (True, None, 204) on success,
             (False, error_msg, 404 or 409) on failure.
    """
    with get_db_cursor(commit=True, config_class=config) as cursor:
        cursor.execute("SELECT id FROM subjects WHERE id = %s;", (subject_id,))
        if not cursor.fetchone():
            return False, f"Subject with ID {subject_id} not found", 404

        cursor.execute("SELECT COUNT(*) as count FROM marks WHERE subject_id = %s;", (subject_id,))
        count = cursor.fetchone()["count"]
        if count > 0:
            return False, "Cannot delete subject because student marks reference it", 409

        cursor.execute("DELETE FROM subjects WHERE id = %s;", (subject_id,))
        return True, None, 204
