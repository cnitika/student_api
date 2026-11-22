import logging
from flask import Flask, request, jsonify, render_template
from config import Config
from db import get_db_cursor
from routes.web_routes import web_bp
from services.student_service import (
    list_students, get_student_by_id, create_student, update_student, delete_student
)
from services.subject_service import (
    list_subjects, get_subject_by_id, create_subject, update_subject, delete_subject
)
from services.mark_service import (
    get_student_marks, add_student_mark, update_mark, delete_mark, get_student_academic_result
)

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("student_api")


def create_app(config_class=None):
    """Application factory for the Student Marks Management System."""
    app = Flask(__name__)
    cfg = config_class or Config
    app.config.from_object(cfg)

    # Validate SECRET_KEY in non-testing environments
    if not app.config.get("SECRET_KEY") and not app.config.get("TESTING"):
        raise RuntimeError("SECRET_KEY environment variable is missing. Please set SECRET_KEY in your .env file.")

    # Register Web UI Blueprint
    app.register_blueprint(web_bp)

    # -------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(error):
        msg = getattr(error, "description", "Bad request")
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": msg}), 400
        return render_template("404.html"), 400

    @app.errorhandler(404)
    def not_found(error):
        msg = getattr(error, "description", "Resource not found")
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": msg}), 404
        return render_template("404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": "Method not allowed"}), 405
        return render_template("404.html"), 405

    @app.errorhandler(409)
    def conflict(error):
        msg = getattr(error, "description", "Conflict")
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": msg}), 409
        return render_template("404.html"), 409

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error on %s: %s", request.path, error)
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": "An internal server error occurred"}), 500
        return render_template("500.html"), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        logger.exception("Unhandled exception on %s: %s", request.path, error)
        if request.path.startswith("/api/") or request.path == "/health":
            return jsonify({"error": "An internal server error occurred"}), 500
        return render_template("500.html"), 500

    # -------------------------------------------------------------
    # System Health Check
    # -------------------------------------------------------------
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

    # -------------------------------------------------------------
    # Students API (/api/students)
    # -------------------------------------------------------------
    @app.route("/api/students", methods=["GET"])
    def api_list_students():
        q = request.args.get("q", "").strip()
        students = list_students(app.config, q=q)
        return jsonify(students), 200

    @app.route("/api/students", methods=["POST"])
    def api_create_student():
        data = request.get_json(silent=True)
        student, error, status_code = create_student(app.config, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(student), 201

    @app.route("/api/students/<int:student_id>", methods=["GET"])
    def api_get_student(student_id):
        student = get_student_by_id(app.config, student_id)
        if not student:
            return jsonify({"error": f"Student with ID {student_id} not found"}), 404
        return jsonify(student), 200

    @app.route("/api/students/<int:student_id>", methods=["PATCH"])
    def api_update_student(student_id):
        data = request.get_json(silent=True)
        student, error, status_code = update_student(app.config, student_id, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(student), 200

    @app.route("/api/students/<int:student_id>", methods=["DELETE"])
    def api_delete_student(student_id):
        success, error, status_code = delete_student(app.config, student_id)
        if not success:
            return jsonify({"error": error}), status_code
        return "", 204

    # -------------------------------------------------------------
    # Subjects API (/api/subjects)
    # -------------------------------------------------------------
    @app.route("/api/subjects", methods=["GET"])
    def api_list_subjects():
        subjects = list_subjects(app.config)
        return jsonify(subjects), 200

    @app.route("/api/subjects", methods=["POST"])
    def api_create_subject():
        data = request.get_json(silent=True)
        subject, error, status_code = create_subject(app.config, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(subject), 201

    @app.route("/api/subjects/<int:subject_id>", methods=["GET"])
    def api_get_subject(subject_id):
        subject = get_subject_by_id(app.config, subject_id)
        if not subject:
            return jsonify({"error": f"Subject with ID {subject_id} not found"}), 404
        return jsonify(subject), 200

    @app.route("/api/subjects/<int:subject_id>", methods=["PATCH"])
    def api_update_subject(subject_id):
        data = request.get_json(silent=True)
        subject, error, status_code = update_subject(app.config, subject_id, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(subject), 200

    @app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
    def api_delete_subject(subject_id):
        success, error, status_code = delete_subject(app.config, subject_id)
        if not success:
            return jsonify({"error": error}), status_code
        return "", 204

    # -------------------------------------------------------------
    # Marks API (/api/students/<id>/marks & /api/marks/<id>)
    # -------------------------------------------------------------
    @app.route("/api/students/<int:student_id>/marks", methods=["GET"])
    def api_get_student_marks(student_id):
        sem = request.args.get("semester", type=int)
        marks, error, status_code = get_student_marks(app.config, student_id, semester=sem)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(marks), 200

    @app.route("/api/students/<int:student_id>/marks", methods=["POST"])
    def api_add_student_mark(student_id):
        data = request.get_json(silent=True)
        mark, error, status_code = add_student_mark(app.config, student_id, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(mark), 201

    @app.route("/api/marks/<int:mark_id>", methods=["PATCH"])
    def api_update_mark(mark_id):
        data = request.get_json(silent=True)
        mark, error, status_code = update_mark(app.config, mark_id, data)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(mark), 200

    @app.route("/api/marks/<int:mark_id>", methods=["DELETE"])
    def api_delete_mark(mark_id):
        success, error, status_code = delete_mark(app.config, mark_id)
        if not success:
            return jsonify({"error": error}), status_code
        return "", 204

    # -------------------------------------------------------------
    # Academic Result API (/api/students/<id>/result)
    # -------------------------------------------------------------
    @app.route("/api/students/<int:student_id>/result", methods=["GET"])
    def api_get_student_result(student_id):
        sem = request.args.get("semester", type=int)
        result, error, status_code = get_student_academic_result(app.config, student_id, semester=sem)
        if error:
            return jsonify({"error": error}), status_code
        return jsonify(result), 200

    return app


# Default application instance
app = create_app()

if __name__ == "__main__":
    debug_mode = app.config.get("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
