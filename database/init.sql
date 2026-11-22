-- Initialization script executed on first-time container startup
CREATE DATABASE IF NOT EXISTS student_test_db;
GRANT ALL PRIVILEGES ON student_test_db.* TO 'student_app'@'%';
GRANT ALL PRIVILEGES ON student_db.* TO 'student_app'@'%';
FLUSH PRIVILEGES;
