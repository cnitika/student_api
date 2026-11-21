import re
import logging
from decimal import Decimal
from flask import Flask, request, jsonify
from config import Config
from db import get_db_cursor
from services.results import calculate_academic_result

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("student_api")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(config_class=None):
    """Application factory for Flask app."""
    app = Flask(__name__)
    cfg = config_class or Config
    app.config.from_object(cfg)

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(error):
        msg = getattr(error, "description", "Bad request")
        return jsonify({"error": msg}), 400

    @app.errorhandler(404)
    def not_found(error):
        msg = getattr(error, "description", "Resource not found")
        return jsonify({"error": msg}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(409)
    def conflict(error):
        msg = getattr(error, "description", "Conflict")
        return jsonify({"error": msg}), 409

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error: %s", error)
        return jsonify({"error": "An internal server error occurred"}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        logger.exception("Unhandled exception: %s", error)
        return jsonify({"error": "An internal server error occurred"}), 500

    # -------------------------------------------------------------
    # General Routes
    # -------------------------------------------------------------
    @app.route("/")
    def home():
        return "Student API is Running Successfully!"

    @app.route("/health")
    def health():
        try:
            with get_db_cursor(config_class=app.config) as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            return jsonify({
                "status": "healthy",
                "database": "connected"
            }), 200
        except Exception as e:
            logger.error("Health check DB connection failed: %s", e)
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected"
            }), 503

    # Legacy compatibility route (returns all students)
    @app.route("/students", methods=["GET"])
    def legacy_get_students():
        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM students ORDER BY id ASC;")
            students = cursor.fetchall()
            return jsonify(students), 200

    # -------------------------------------------------------------
    # Students API
    # -------------------------------------------------------------
    @app.route("/api/students", methods=["GET"])
    def list_students():
        q = request.args.get("q", "").strip()
        with get_db_cursor(config_class=app.config) as cursor:
            if q:
                if q.isdigit():
                    cursor.execute(
                        """
                        SELECT * FROM students
                        WHERE id = %s OR roll_no = %s OR student_name LIKE %s
                        ORDER BY id ASC;
                        """,
                        (int(q), q, f"%{q}%")
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM students
                        WHERE roll_no = %s OR student_name LIKE %s
                        ORDER BY id ASC;
                        """,
                        (q, f"%{q}%")
                    )
            else:
                cursor.execute("SELECT * FROM students ORDER BY id ASC;")
            students = cursor.fetchall()
            return jsonify(students), 200

    @app.route("/api/students", methods=["POST"])
    def create_student():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        required_fields = [
            "roll_no", "student_name", "email",
            "department", "course", "academic_year", "semester"
        ]
        for field in required_fields:
            if field not in data or data[field] is None or str(data[field]).strip() == "":
                return jsonify({"error": f"'{field}' is required"}), 400

        email = str(data["email"]).strip()
        if not EMAIL_REGEX.match(email):
            return jsonify({"error": "Invalid email format"}), 400

        try:
            semester = int(data["semester"])
            if semester < 1 or semester > 12:
                return jsonify({"error": "Semester must be an integer between 1 and 12"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Semester must be a valid integer"}), 400

        roll_no = str(data["roll_no"]).strip()
        student_name = str(data["student_name"]).strip()
        department = str(data["department"]).strip()
        course = str(data["course"]).strip()
        academic_year = str(data["academic_year"]).strip()

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            # Check roll_no or email duplicates
            cursor.execute(
                "SELECT id, roll_no, email FROM students WHERE roll_no = %s OR email = %s;",
                (roll_no, email)
            )
            existing = cursor.fetchone()
            if existing:
                if existing["roll_no"] == roll_no:
                    return jsonify({"error": f"Student with roll number '{roll_no}' already exists"}), 409
                if existing["email"] == email:
                    return jsonify({"error": f"Student with email '{email}' already exists"}), 409

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
            return jsonify(student), 201

    @app.route("/api/students/<int:student_id>", methods=["GET"])
    def get_student(student_id):
        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
            student = cursor.fetchone()
            if not student:
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404
            return jsonify(student), 200

    @app.route("/api/students/<int:student_id>", methods=["PATCH"])
    def update_student(student_id):
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        allowed_fields = [
            "roll_no", "student_name", "email",
            "department", "course", "academic_year", "semester"
        ]
        updates = {}
        for f in allowed_fields:
            if f in data:
                updates[f] = data[f]

        if not updates:
            return jsonify({"error": "No valid fields provided for update"}), 400

        if "email" in updates:
            email = str(updates["email"]).strip()
            if not EMAIL_REGEX.match(email):
                return jsonify({"error": "Invalid email format"}), 400
            updates["email"] = email

        if "semester" in updates:
            try:
                sem = int(updates["semester"])
                if sem < 1 or sem > 12:
                    return jsonify({"error": "Semester must be an integer between 1 and 12"}), 400
                updates["semester"] = sem
            except (ValueError, TypeError):
                return jsonify({"error": "Semester must be a valid integer"}), 400

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
            student = cursor.fetchone()
            if not student:
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404

            # Duplicate roll_no or email check for other students
            if "roll_no" in updates and updates["roll_no"] != student["roll_no"]:
                cursor.execute(
                    "SELECT id FROM students WHERE roll_no = %s AND id != %s;",
                    (updates["roll_no"], student_id)
                )
                if cursor.fetchone():
                    return jsonify({"error": f"Roll number '{updates['roll_no']}' is already in use"}), 409

            if "email" in updates and updates["email"] != student["email"]:
                cursor.execute(
                    "SELECT id FROM students WHERE email = %s AND id != %s;",
                    (updates["email"], student_id)
                )
                if cursor.fetchone():
                    return jsonify({"error": f"Email '{updates['email']}' is already in use"}), 409

            set_clauses = [f"{k} = %s" for k in updates.keys()]
            values = list(updates.values())
            values.append(student_id)

            sql = f"UPDATE students SET {', '.join(set_clauses)} WHERE id = %s;"
            cursor.execute(sql, tuple(values))

            cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
            updated_student = cursor.fetchone()
            return jsonify(updated_student), 200

    @app.route("/api/students/<int:student_id>", methods=["DELETE"])
    def delete_student(student_id):
        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT id FROM students WHERE id = %s;", (student_id,))
            if not cursor.fetchone():
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404

            cursor.execute("DELETE FROM students WHERE id = %s;", (student_id,))
            return "", 204

    # -------------------------------------------------------------
    # Subjects API
    # -------------------------------------------------------------
    @app.route("/api/subjects", methods=["GET"])
    def list_subjects():
        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM subjects ORDER BY id ASC;")
            subjects = cursor.fetchall()
            return jsonify(subjects), 200

    @app.route("/api/subjects", methods=["POST"])
    def create_subject():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        required = ["subject_code", "subject_name", "max_marks"]
        for f in required:
            if f not in data or data[f] is None or str(data[f]).strip() == "":
                return jsonify({"error": f"'{f}' is required"}), 400

        code = str(data["subject_code"]).strip()
        name = str(data["subject_name"]).strip()

        try:
            max_marks = Decimal(str(data["max_marks"]))
            if max_marks <= Decimal("0"):
                return jsonify({"error": "max_marks must be greater than 0"}), 400
        except Exception:
            return jsonify({"error": "max_marks must be a valid positive number"}), 400

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT id FROM subjects WHERE subject_code = %s;", (code,))
            if cursor.fetchone():
                return jsonify({"error": f"Subject code '{code}' already exists"}), 409

            cursor.execute(
                "INSERT INTO subjects (subject_code, subject_name, max_marks) VALUES (%s, %s, %s);",
                (code, name, float(max_marks))
            )
            sub_id = cursor.lastrowid

            cursor.execute("SELECT * FROM subjects WHERE id = %s;", (sub_id,))
            subject = cursor.fetchone()
            return jsonify(subject), 201

    @app.route("/api/subjects/<int:subject_id>", methods=["GET"])
    def get_subject(subject_id):
        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
            sub = cursor.fetchone()
            if not sub:
                return jsonify({"error": f"Subject with ID {subject_id} not found"}), 404
            return jsonify(sub), 200

    @app.route("/api/subjects/<int:subject_id>", methods=["PATCH"])
    def update_subject(subject_id):
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        allowed = ["subject_code", "subject_name", "max_marks"]
        updates = {k: data[k] for k in allowed if k in data}
        if not updates:
            return jsonify({"error": "No valid fields provided for update"}), 400

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
            subject = cursor.fetchone()
            if not subject:
                return jsonify({"error": f"Subject with ID {subject_id} not found"}), 404

            if "subject_code" in updates:
                new_code = str(updates["subject_code"]).strip()
                if new_code != subject["subject_code"]:
                    cursor.execute("SELECT id FROM subjects WHERE subject_code = %s AND id != %s;", (new_code, subject_id))
                    if cursor.fetchone():
                        return jsonify({"error": f"Subject code '{new_code}' already exists"}), 409
                updates["subject_code"] = new_code

            if "max_marks" in updates:
                try:
                    new_max = Decimal(str(updates["max_marks"]))
                    if new_max <= Decimal("0"):
                        return jsonify({"error": "max_marks must be greater than 0"}), 400
                    # Validate that no existing student marks exceed this new max_marks
                    cursor.execute("SELECT MAX(marks_obtained) as highest FROM marks WHERE subject_id = %s;", (subject_id,))
                    highest = cursor.fetchone()["highest"]
                    if highest is not None and Decimal(str(highest)) > new_max:
                        return jsonify({"error": f"Cannot set max_marks to {new_max} because existing marks obtained is {highest}"}), 400
                    updates["max_marks"] = float(new_max)
                except Exception:
                    return jsonify({"error": "max_marks must be a valid positive number"}), 400

            set_clauses = [f"{k} = %s" for k in updates.keys()]
            values = list(updates.values())
            values.append(subject_id)

            sql = f"UPDATE subjects SET {', '.join(set_clauses)} WHERE id = %s;"
            cursor.execute(sql, tuple(values))

            cursor.execute("SELECT * FROM subjects WHERE id = %s;", (subject_id,))
            updated_sub = cursor.fetchone()
            return jsonify(updated_sub), 200

    @app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
    def delete_subject(subject_id):
        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT id FROM subjects WHERE id = %s;", (subject_id,))
            if not cursor.fetchone():
                return jsonify({"error": f"Subject with ID {subject_id} not found"}), 404

            # Check if any marks reference this subject
            cursor.execute("SELECT COUNT(*) as count FROM marks WHERE subject_id = %s;", (subject_id,))
            count = cursor.fetchone()["count"]
            if count > 0:
                return jsonify({"error": "Cannot delete subject because student marks reference it"}), 409

            cursor.execute("DELETE FROM subjects WHERE id = %s;", (subject_id,))
            return "", 204

    # -------------------------------------------------------------
    # Marks API
    # -------------------------------------------------------------
    @app.route("/api/students/<int:student_id>/marks", methods=["GET"])
    def get_student_marks(student_id):
        sem = request.args.get("semester", type=int)
        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT id FROM students WHERE id = %s;", (student_id,))
            if not cursor.fetchone():
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404

            if sem is not None:
                cursor.execute(
                    """
                    SELECT m.id, m.student_id, m.subject_id, m.semester, m.marks_obtained,
                           s.subject_code, s.subject_name, s.max_marks, m.created_at, m.updated_at
                    FROM marks m
                    JOIN subjects s ON m.subject_id = s.id
                    WHERE m.student_id = %s AND m.semester = %s
                    ORDER BY s.subject_code ASC;
                    """,
                    (student_id, sem)
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
            return jsonify(marks), 200

    @app.route("/api/students/<int:student_id>/marks", methods=["POST"])
    def add_student_mark(student_id):
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        if "subject_id" not in data or data["subject_id"] is None:
            return jsonify({"error": "'subject_id' is required"}), 400
        if "marks_obtained" not in data or data["marks_obtained"] is None:
            return jsonify({"error": "'marks_obtained' is required"}), 400

        try:
            subject_id = int(data["subject_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "'subject_id' must be an integer"}), 400

        try:
            marks_obtained = Decimal(str(data["marks_obtained"]))
            if marks_obtained < Decimal("0"):
                return jsonify({"error": "marks_obtained cannot be negative"}), 400
        except Exception:
            return jsonify({"error": "marks_obtained must be a valid numeric value"}), 400

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT id, semester FROM students WHERE id = %s;", (student_id,))
            student = cursor.fetchone()
            if not student:
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404

            # Default semester to student's registered semester if omitted
            if "semester" in data and data["semester"] is not None:
                try:
                    semester = int(data["semester"])
                    if semester < 1 or semester > 12:
                        return jsonify({"error": "Semester must be between 1 and 12"}), 400
                except (ValueError, TypeError):
                    return jsonify({"error": "Semester must be a valid integer"}), 400
            else:
                semester = student["semester"]

            cursor.execute("SELECT id, subject_code, subject_name, max_marks FROM subjects WHERE id = %s;", (subject_id,))
            subject = cursor.fetchone()
            if not subject:
                return jsonify({"error": f"Subject with ID {subject_id} not found"}), 404

            max_marks = Decimal(str(subject["max_marks"]))
            if marks_obtained > max_marks:
                return jsonify({
                    "error": f"Marks obtained ({marks_obtained}) cannot exceed subject maximum marks ({max_marks})"
                }), 400

            # Duplicate mark check
            cursor.execute(
                """
                SELECT id FROM marks
                WHERE student_id = %s AND subject_id = %s AND semester = %s;
                """,
                (student_id, subject_id, semester)
            )
            if cursor.fetchone():
                return jsonify({
                    "error": f"Marks already recorded for subject '{subject['subject_code']}' in semester {semester}"
                }), 409

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
            return jsonify(created_mark), 201

    @app.route("/api/marks/<int:mark_id>", methods=["PATCH"])
    def update_mark(mark_id):
        data = request.get_json(silent=True)
        if not data or "marks_obtained" not in data or data["marks_obtained"] is None:
            return jsonify({"error": "'marks_obtained' is required in body"}), 400

        try:
            new_marks = Decimal(str(data["marks_obtained"]))
            if new_marks < Decimal("0"):
                return jsonify({"error": "marks_obtained cannot be negative"}), 400
        except Exception:
            return jsonify({"error": "marks_obtained must be a valid numeric value"}), 400

        with get_db_cursor(commit=True, config_class=app.config) as cursor:
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
                return jsonify({"error": f"Mark record with ID {mark_id} not found"}), 404

            max_marks = Decimal(str(mark["max_marks"]))
            if new_marks > max_marks:
                return jsonify({
                    "error": f"Marks obtained ({new_marks}) cannot exceed maximum marks ({max_marks})"
                }), 400

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
            return jsonify(updated), 200

    @app.route("/api/marks/<int:mark_id>", methods=["DELETE"])
    def delete_mark(mark_id):
        with get_db_cursor(commit=True, config_class=app.config) as cursor:
            cursor.execute("SELECT id FROM marks WHERE id = %s;", (mark_id,))
            if not cursor.fetchone():
                return jsonify({"error": f"Mark record with ID {mark_id} not found"}), 404

            cursor.execute("DELETE FROM marks WHERE id = %s;", (mark_id,))
            return "", 204

    # -------------------------------------------------------------
    # Academic Result API
    # -------------------------------------------------------------
    @app.route("/api/students/<int:student_id>/result", methods=["GET"])
    def get_student_result(student_id):
        sem = request.args.get("semester", type=int)

        with get_db_cursor(config_class=app.config) as cursor:
            cursor.execute("SELECT * FROM students WHERE id = %s;", (student_id,))
            student = cursor.fetchone()
            if not student:
                return jsonify({"error": f"Student with ID {student_id} not found"}), 404

            target_sem = sem if sem is not None else student["semester"]

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

            result = calculate_academic_result(
                student_info=student,
                marks_records=records,
                pass_threshold=app.config.get("PASS_THRESHOLD_PERCENT", Decimal("35.00")),
                grade_scale=app.config.get("GRADE_SCALE"),
                semester=target_sem
            )
            return jsonify(result), 200

    return app


# Default application instance for development / WSGI
app = create_app()

if __name__ == "__main__":
    debug_mode = app.config.get("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
