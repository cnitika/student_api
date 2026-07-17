# Student API - Flask + MySQL + Docker
# Student Management REST API

A complete CRUD REST API built with Flask, MySQL, and Docker — demonstrating backend development fundamentals including database integration, containerization, and secure credential management.

## Features
- **GET** `/students` — Retrieve all students
- **POST** `/students` — Create a new student
- **PATCH** `/students/<id>` — Update student details
- **DELETE** `/students/<id>` — Remove a student

## Tech Stack
- **Backend:** Python, Flask
- **Database:** MySQL (via pymysql)
- **Containerization:** Docker
- **Version Control:** Git

## Key Implementation Details
- Environment variables (`.env`) used to secure database credentials
- Proper error handling with try/except blocks across all endpoints
- Dockerized application for consistent deployment across environments

## How to Run

### Using Docker (Recommended)
\`\`\`bash
docker build -t student-api .
docker run -p 5000:5000 student-api
\`\`\`

### Without Docker
\`\`\`bash
pip install -r requirements.txt
python app.py
\`\`\`

## API Testing
Tested using Postman with all CRUD operations verified.

## What I Learned
- REST API design principles and HTTP methods
- Database connection handling and query security (parameterized queries)
- Docker networking concepts (host.docker.internal)
- Git version control including merge conflict resolution
