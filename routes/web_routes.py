from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from services.student_service import (
    list_students, get_student_by_id, create_student, update_student, delete_student
)
from services.subject_service import (
    list_subjects, get_subject_by_id, create_subject, update_subject, delete_subject
)
from services.mark_service import (
    get_student_marks, add_student_mark, update_mark, delete_mark, get_student_academic_result
)
from services.dashboard_service import get_dashboard_stats

web_bp = Blueprint("web", __name__)


# -------------------------------------------------------------
# Dashboard
# -------------------------------------------------------------
@web_bp.route("/")
def dashboard():
    stats = get_dashboard_stats(current_app.config)
    return render_template("dashboard.html", stats=stats, active_page="dashboard")


# -------------------------------------------------------------
# Students
# -------------------------------------------------------------
@web_bp.route("/students")
def students_list():
    q = request.args.get("q", "").strip()
    students = list_students(current_app.config, q=q)
    return render_template(
        "students.html",
        students=students,
        search_query=q,
        active_page="students"
    )


@web_bp.route("/students/new", methods=["GET", "POST"])
def add_student_page():
    if request.method == "POST":
        student, error, status_code = create_student(current_app.config, request.form)
        if error:
            flash(error, "error")
            return render_template("add_student.html", form_data=request.form, active_page="add_student"), 400
        flash(f"Student '{student['student_name']}' successfully registered!", "success")
        return redirect(url_for("web.students_list"))

    return render_template("add_student.html", form_data={}, active_page="add_student")


@web_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student_page(student_id):
    student = get_student_by_id(current_app.config, student_id)
    if not student:
        flash(f"Student with ID {student_id} not found", "error")
        return redirect(url_for("web.students_list")), 404

    if request.method == "POST":
        updated, error, status_code = update_student(current_app.config, student_id, request.form)
        if error:
            flash(error, "error")
            return render_template("edit_student.html", student=student, form_data=request.form, active_page="students"), 400
        flash(f"Student '{updated['student_name']}' successfully updated!", "success")
        return redirect(url_for("web.students_list"))

    return render_template("edit_student.html", student=student, form_data={}, active_page="students")


@web_bp.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student_action(student_id):
    success, error, status_code = delete_student(current_app.config, student_id)
    if not success:
        flash(error, "error")
    else:
        flash("Student and associated marks successfully deleted.", "success")
    return redirect(url_for("web.students_list"))


# -------------------------------------------------------------
# Subjects
# -------------------------------------------------------------
@web_bp.route("/subjects")
def subjects_list():
    subjects = list_subjects(current_app.config)
    return render_template(
        "subjects.html",
        subjects=subjects,
        form_data={},
        active_page="subjects"
    )


@web_bp.route("/subjects/new", methods=["POST"])
def add_subject_action():
    subject, error, status_code = create_subject(current_app.config, request.form)
    if error:
        flash(error, "error")
        subjects = list_subjects(current_app.config)
        return render_template("subjects.html", subjects=subjects, form_data=request.form, active_page="subjects"), 400
    flash(f"Subject '{subject['subject_code']} - {subject['subject_name']}' added successfully!", "success")
    return redirect(url_for("web.subjects_list"))


@web_bp.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
def edit_subject_page(subject_id):
    subject = get_subject_by_id(current_app.config, subject_id)
    if not subject:
        flash(f"Subject with ID {subject_id} not found", "error")
        return redirect(url_for("web.subjects_list")), 404

    if request.method == "POST":
        updated, error, status_code = update_subject(current_app.config, subject_id, request.form)
        if error:
            flash(error, "error")
            return render_template("edit_subject.html", subject=subject, form_data=request.form, active_page="subjects"), 400
        flash(f"Subject '{updated['subject_code']}' successfully updated!", "success")
        return redirect(url_for("web.subjects_list"))

    return render_template("edit_subject.html", subject=subject, form_data={}, active_page="subjects")


@web_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
def delete_subject_action(subject_id):
    success, error, status_code = delete_subject(current_app.config, subject_id)
    if not success:
        flash(error, "error")
    else:
        flash("Subject successfully deleted.", "success")
    return redirect(url_for("web.subjects_list"))


# -------------------------------------------------------------
# Marks Entry & Overview
# -------------------------------------------------------------
@web_bp.route("/students/<int:student_id>/marks")
def student_marks_page(student_id):
    student = get_student_by_id(current_app.config, student_id)
    if not student:
        flash(f"Student with ID {student_id} not found", "error")
        return redirect(url_for("web.students_list")), 404

    sem = request.args.get("semester", type=int)
    marks, error, status_code = get_student_marks(current_app.config, student_id, semester=sem)

    return render_template(
        "student_marks.html",
        student=student,
        marks=marks or [],
        selected_semester=sem,
        active_page="students"
    )


@web_bp.route("/students/<int:student_id>/marks/entry", methods=["GET", "POST"])
def marks_entry_page(student_id):
    student = get_student_by_id(current_app.config, student_id)
    if not student:
        flash(f"Student with ID {student_id} not found", "error")
        return redirect(url_for("web.students_list")), 404

    subjects = list_subjects(current_app.config)

    if request.method == "POST":
        # Form supports multi-row submission: subject_ids[], semesters[], marks_obtained[]
        subject_ids = request.form.getlist("subject_ids[]")
        semesters = request.form.getlist("semesters[]")
        marks_obtained = request.form.getlist("marks_obtained[]")

        # If single field was submitted (fallback)
        if not subject_ids and "subject_id" in request.form:
            subject_ids = [request.form.get("subject_id")]
            semesters = [request.form.get("semester")]
            marks_obtained = [request.form.get("marks_obtained")]

        if not subject_ids or all(not str(s).strip() for s in subject_ids):
            flash("Please select at least one subject to record marks.", "error")
            existing_marks, _, _ = get_student_marks(current_app.config, student_id)
            return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400

        # Validate all rows first to guarantee atomic behavior
        valid_rows = []
        seen_combinations = set()

        for idx, sub_id in enumerate(subject_ids):
            if not sub_id or not str(sub_id).strip():
                continue

            sem = semesters[idx] if idx < len(semesters) else student["semester"]
            m_val = marks_obtained[idx] if idx < len(marks_obtained) else None

            # Validate numeric marks
            if m_val is None or str(m_val).strip() == "":
                flash("Marks obtained cannot be empty for selected subject.", "error")
                existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400

            try:
                dec_val = Decimal(str(m_val).strip())
                if dec_val < Decimal("0"):
                    flash("Marks obtained cannot be negative.", "error")
                    existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                    return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400
            except Exception:
                flash("Marks obtained must be a valid numeric number.", "error")
                existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400

            try:
                sem_int = int(sem) if sem else student["semester"]
                if sem_int < 1 or sem_int > 12:
                    flash("Semester must be between 1 and 12.", "error")
                    existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                    return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400
            except Exception:
                flash("Invalid semester value.", "error")
                existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400

            combo = (int(sub_id), sem_int)
            if combo in seen_combinations:
                flash("Duplicate subject specified in the same form submission.", "error")
                existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400
            seen_combinations.add(combo)

            valid_rows.append({
                "subject_id": int(sub_id),
                "semester": sem_int,
                "marks_obtained": dec_val
            })

        # Save all valid rows
        added_count = 0
        for row in valid_rows:
            mark, error, status_code = add_student_mark(current_app.config, student_id, row)
            if error:
                flash(error, "error")
                existing_marks, _, _ = get_student_marks(current_app.config, student_id)
                return render_template("marks_entry.html", student=student, subjects=subjects, existing_marks=existing_marks or [], active_page="students"), 400
            added_count += 1

        flash(f"Successfully recorded marks for {added_count} subject(s)!", "success")
        return redirect(url_for("web.marks_entry_page", student_id=student_id))

    existing_marks, _, _ = get_student_marks(current_app.config, student_id)
    return render_template(
        "marks_entry.html",
        student=student,
        subjects=subjects,
        existing_marks=existing_marks or [],
        active_page="students"
    )


@web_bp.route("/students/<int:student_id>/marks/<int:mark_id>/update", methods=["POST"])
def update_mark_action(student_id, mark_id):
    updated, error, status_code = update_mark(current_app.config, mark_id, request.form)
    if error:
        flash(error, "error")
    else:
        flash("Marks updated successfully.", "success")
    return redirect(url_for("web.marks_entry_page", student_id=student_id))


@web_bp.route("/students/<int:student_id>/marks/<int:mark_id>/delete", methods=["POST"])
def delete_mark_action(student_id, mark_id):
    success, error, status_code = delete_mark(current_app.config, mark_id)
    if not success:
        flash(error, "error")
    else:
        flash("Marks record deleted.", "success")
    return redirect(url_for("web.marks_entry_page", student_id=student_id))


# -------------------------------------------------------------
# Academic Result Sheet
# -------------------------------------------------------------
@web_bp.route("/students/<int:student_id>/result")
def student_result_page(student_id):
    sem = request.args.get("semester", type=int)
    result, error, status_code = get_student_academic_result(current_app.config, student_id, semester=sem)
    if error:
        flash(error, "error")
        return redirect(url_for("web.students_list")), 404

    return render_template("result.html", result=result, active_page="students")
