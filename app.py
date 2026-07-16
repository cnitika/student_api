from flask import Flask, request, jsonify
from db import get_connection

app = Flask(__name__)



@app.route("/")
def home():
    return "Student API is Running Successfully!"


@app.route("/students", methods=["GET"])
def get_students():
    print("GET /students called")
    return jsonify({"message": "Students route works"})



@app.route("/students", methods=["POST"])
def create_student():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        name = data.get("name")
        email = data.get("email")
        course = data.get("course")

        if not name or not email:
            return jsonify({"error": "Name and Email are required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO students (name, email, course)
            VALUES (%s, %s, %s)
            """,
            (name, email, course)
        )

        conn.commit()

        student_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({
            "id": student_id,
            "name": name,
            "email": email,
            "course": course
        }), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/students/<int:student_id>", methods=["PATCH"])
def update_student(student_id):
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        course = data.get("course")

        if not course:
            return jsonify({"error": "Course is required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE students
            SET course = %s
            WHERE id = %s
            """,
            (course, student_id)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Student updated successfully",
            "id": student_id
        }), 200

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM students WHERE id = %s",
            (student_id,)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return "", 204

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500


# Show All Routes

print(app.url_map)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
