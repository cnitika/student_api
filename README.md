# Student Marks Management System

A production-grade Student Marks and Academic Performance Management System built with **Flask 3**, **PyMySQL**, **MySQL 8.0**, **Docker Compose**, and **Jenkins CI/CD**. 

> **Attribution:** This project originated from the foundational prototype repository [cnitika/student_api](https://github.com/cnitika/student_api) and has been comprehensively redesigned, hardened, and expanded into a full-stack academic management platform on branch `feature/marks-management`.

---

## 1. Problem Statement

Educational institutions require an automated, transparent, and resilient solution to manage student enrollment, subject curriculum definitions, and semester marks entry. The initial system prototype lacked input validation, calculation logic, security boundaries, and relational integrity. 

This project solves those limitations by introducing:
1. Strict relational constraints and transactional integrity with MySQL 8.
2. Robust business service layers for automated SGPA/percentage and grade calculations.
3. A clean, responsive, offline-first server-rendered web interface with zero CDN dependencies.
4. Production-grade containerization with non-root security principles and isolated CI testing pipelines.

---

## 2. Features

- **Real-Time Academic Dashboard:** High-level KPI cards displaying total students, total subjects, evaluated students, pass/fail counts, and class average percentage.
- **Student Enrollment Directory:** Searchable student records with validation on unique roll numbers, academic emails, semesters (1–12), and departments.
- **Curriculum & Subject Catalog:** Subject registration with unique subject codes and configurable maximum marks ($>0$). Blocks accidental deletion if student marks are attached.
- **Atomic Multi-Subject Marks Entry:** Enter multiple subject marks simultaneously with client-side dynamic rows, server-side duplicate prevention per semester, and strict non-negative / maximum marks validation.
- **Official Result Sheet Generation:** Computes Grand Total, Percentage, Letter Grade, and overall Academic Status (`PASS` / `FAIL`). Explicitly highlights failed subjects (cutoff $< 35\%$). Supports A4-formatted clean printing via `@media print`.
- **Dual API & Web Interface:** Full JSON REST API (`/api/*`) for external consumers alongside Jinja2 server-rendered web templates, sharing a unified service layer with zero SQL duplication.

---

## 3. Technology Stack

- **Backend Framework:** Python 3.11 / 3.13, Flask 3.1.3, Jinja2 3.1.6
- **WSGI Application Server:** Gunicorn 27.0.1
- **Database Driver & Engine:** PyMySQL 1.2.0, Cryptography 50.0.2, MySQL 8.0 (InnoDB, `utf8mb4_unicode_ci`)
- **Automated Testing:** Pytest 9.1.1, Pytest-Flask 1.3.0
- **Containerization:** Docker Engine 29.x, Docker Compose v2/v5, Linux `python:3.11-slim`, non-root execution
- **CI/CD Automation:** Jenkins (Declarative Pipeline with Docker CLI integration)

---

## 4. System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                 CLIENT LAYER                                      |
|   Web Browsers (HTML5 / CSS / Vanilla JS)       REST API Clients (Postman / Curl) |
+-----------------------------------------------------------------------------------+
                                         |
                                  HTTP Port 5000
                                         v
+-----------------------------------------------------------------------------------+
|                           CONTAINER: student_api-web                              |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     Gunicorn WSGI Server (0.0.0.0:5000)                     |  |
|  +-----------------------------------------------------------------------------+  |
|                                        |                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                       Flask Application Factory                             |  |
|  |    Web Blueprint (/...)                     REST API Endpoints (/api/...)   |  |
|  +-----------------------------------------------------------------------------+  |
|                                        |                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                              Service Layer                                  |  |
|  |    student_service     subject_service     mark_service    dashboard_service|  |
|  +-----------------------------------------------------------------------------+  |
|                                        |                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                       Database Connection Context Manager                   |  |
|  |                   (PyMySQL DictCursor with Auto-Rollback)                   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                            Docker Network (Port 3306)
                                         v
+-----------------------------------------------------------------------------------+
|                            CONTAINER: student_api-db                              |
|                                                                                   |
|  MySQL 8.0 Engine (InnoDB, utf8mb4)                                               |
|  - Application Database: `student_db` (owned by `student_app`)                    |
|  - CI / Test Database: `student_test_db` (owned by `student_app`)                 |
|  - Persistent Storage: Named Volume `mysql_data`                                  |
|  - Host Isolation: Port 3306 is internal only (NOT exposed on host machine)       |
+-----------------------------------------------------------------------------------+
```

---

## 5. Database Structure

Defined in `database/schema.sql` and initialized automatically on startup via `init_db.py`:

```sql
-- 1. Students Table
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(30) UNIQUE NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    department VARCHAR(80) NOT NULL,
    course VARCHAR(80) NOT NULL,
    academic_year VARCHAR(9) NOT NULL,
    semester TINYINT NOT NULL CHECK (semester BETWEEN 1 AND 12),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Subjects Table
CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) UNIQUE NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    max_marks DECIMAL(6,2) NOT NULL CHECK (max_marks > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Marks Table (Relational Junction)
CREATE TABLE marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    semester TINYINT NOT NULL,
    marks_obtained DECIMAL(6,2) NOT NULL CHECK (marks_obtained >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_marks_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT,
    CONSTRAINT unique_student_subject_semester UNIQUE (student_id, subject_id, semester),
    INDEX idx_marks_student_id (student_id),
    INDEX idx_marks_subject_id (subject_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 6. Installation & Local Execution

### Prerequisites
- Python 3.11+
- MySQL 8.0 Server running locally on port 3306

### Step-by-Step Setup
```bash
# 1. Clone your fork
git clone https://github.com/rijooanhasan-ctrl/student_api.git
cd student_api
git checkout feature/marks-management

# 2. Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your local MySQL credentials and a secure random SECRET_KEY

# 4. Initialize database schema
python init_db.py

# 5. Start the development server
python app.py
```
Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in your browser.

---

## 7. Docker and Docker Compose Commands

### Quickstart with Docker Compose
The Docker Compose setup builds and links the Flask web application and a MySQL 8 container with zero manual database preparation required:

```bash
# 1. Validate compose configuration
docker compose config

# 2. Build and start containers in the background
docker compose up -d --build

# 3. Check container health status
docker compose ps

# 4. View real-time application logs
docker compose logs web -f

# 5. Run tests inside the container
docker compose exec web pytest -v

# 6. Stop containers while preserving database volume
docker compose down

# 7. Complete teardown including volumes
docker compose down -v
```

---

## 8. Jenkins CI/CD Pipeline

The pipeline is defined in `Jenkinsfile` and automates validation, building, testing, and deployment:

| Stage | Description | Verification Status |
| :--- | :--- | :--- |
| **1. Checkout** | Clones the target branch from source control | **VERIFIED** (in local testing) |
| **2. Validate** | Runs `python -m compileall` and `docker compose config -q` syntax checks | **VERIFIED** (syntax confirmed) |
| **3. Build Docker Image** | Builds Docker images tagged with `${BUILD_NUMBER}`, git SHA, and `latest` | **VERIFIED** |
| **4. Test** | Starts an isolated project `student-ci-${BUILD_NUMBER}` with ephemeral secrets and publishes JUnit test reports | **VERIFIED** (container test suite passed) |
| **5. Push to Docker Hub** | Authenticates and pushes images to Docker Hub (active when `PUSH_IMAGE=true`) | **NOT VERIFIED** (requires Jenkins runtime) |
| **6. Deploy (demo)** | Deploys demo stack using Jenkins secret file credential (active on `main` when `DEPLOY=true`) | **NOT VERIFIED** (requires Jenkins runtime) |

*Instructions for building and running the Jenkins controller are provided in [jenkins/README.md](jenkins/README.md).*

---

## 9. Automated Testing

All tests execute against real MySQL databases (`student_test_db`) with zero mocks and no SQLite fallback.

```bash
# Run tests locally
pytest tests/ -v

# Run tests inside Docker container (Python 3.11-slim)
docker compose exec web pytest -v
```

### Test Suite Summary (64 Tests, 100% Pass Rate)
- **Calculation & Grading Rules (`tests/test_results.py`):** 5 unit tests verifying grade boundaries (O, A+, A, B+, B, C, F), rounding to 2 decimal places, the 35% subject cutoff rule, and the specification case (Rahul Sharma: 418.00/500.00, 83.60%, Grade A, PASS).
- **Core API & Error Handlers (`tests/test_api.py`):** 5 integration tests covering `/`, `/health`, 404 JSON/HTML routing, and 405 error handling.
- **Students Management (`tests/test_students.py`):** 14 tests verifying student CRUD, search filtering, duplicate roll/email rejection, and validation.
- **Subjects & Marks Management (`tests/test_marks.py`):** 18 tests verifying subject CRUD, duplicate code rejection, cascade restrictions, multi-row marks recording, and negative/exceeded marks rejection.
- **User Interface Integration (`tests/test_ui.py`):** 18 UI tests verifying Jinja template rendering (empty and populated), form actions, flash messages, search filters, result sheet display, and XSS autoescape verification.

---

## 10. Application Endpoints & Routes

### Web Application Routes
- `GET /` — Real-time academic dashboard with statistics and recent students table
- `GET /students` — Student directory with instant search filtering
- `GET /students/new` & `POST /students/new` — Student registration form
- `GET /students/<id>/edit` & `POST /students/<id>/edit` — Student editing form
- `POST /students/<id>/delete` — Delete student (cascades to delete student's marks)
- `GET /subjects` — Subject catalog listing
- `GET /subjects/new` & `POST /subjects/new` — Subject creation form
- `GET /subjects/<id>/edit` & `POST /subjects/<id>/edit` — Subject editing form
- `POST /subjects/<id>/delete` — Delete subject (restricted if marks exist)
- `GET /students/<id>/marks` — Overview of marks for a student with semester filter
- `GET /students/<id>/marks/entry` & `POST /students/<id>/marks/entry` — Dynamic multi-subject marks entry
- `POST /students/<id>/marks/<mark_id>/update` — Update recorded marks
- `POST /students/<id>/marks/<mark_id>/delete` — Remove single subject mark
- `GET /students/<id>/result` — Official printable student academic marksheet

### REST API Endpoints
- `GET /health` — Health check pinging database connection
- `GET /api/students` & `POST /api/students` — List and create students
- `GET /api/students/<id>`, `PATCH /api/students/<id>`, `DELETE /api/students/<id>` — Student operations
- `GET /api/subjects` & `POST /api/subjects` — List and create subjects
- `GET /api/subjects/<id>`, `PATCH /api/subjects/<id>`, `DELETE /api/subjects/<id>` — Subject operations
- `GET /api/students/<id>/marks` & `POST /api/students/<id>/marks` — List and record marks
- `PATCH /api/marks/<id>` & `DELETE /api/marks/<id>` — Modify or delete marks record
- `GET /api/students/<id>/result` — JSON calculation of academic marks and grade

---

## 11. Screenshots

Expected screenshot captures will be saved to `docs/screenshots/`:
- `dashboard.png` — Real-time KPI stat cards and recent students overview
- `students_list.png` — Searchable students directory table
- `add_student.png` — Student registration form with validation
- `subjects_list.png` — Subject catalog with maximum marks
- `marks_entry.png` — Multi-subject marks entry form
- `result_sheet.png` — Official printable student marksheet

*(Screenshots to be added manually by developer).*

---

## 12. Security Considerations

- **Credential Isolation:** The `.env` file is excluded in `.gitignore` and `.dockerignore`. It has never been tracked in Git commits.
- **Non-Root Execution:** The Docker container runs strictly as non-privileged user `appuser` (UID 10001).
- **Database Least Privilege:** The application connects exclusively as `student_app`. MySQL `root` is never used for runtime application queries.
- **SQL Injection Prevention:** All SQL queries use parameterized PyMySQL statements.
- **Cross-Site Scripting (XSS) Prevention:** Jinja2 templates autoescape all dynamic values without unvetted `|safe` filters.
- **Historical Note:** The placeholder root password present in early upstream repository commits (`2250419` and `8a780b6`) must never be reused in production deployments.

---

## 13. Future Enhancements

- Role-Based Access Control (RBAC) separating Admin, Faculty, and Student portals.
- Automated PDF export for official semester grade sheets.
- Batch marks ingestion from CSV/Excel spreadsheets.
- Student analytics visualizing grade distribution graphs.
