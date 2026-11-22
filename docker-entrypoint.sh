#!/bin/sh
set -e

# If arguments are passed (e.g., pytest, bash, python), run them directly
if [ "$#" -gt 0 ] && [ "$1" != "gunicorn" ]; then
    exec "$@"
fi

echo "Running database initialization..."
python init_db.py

echo "Starting Gunicorn WSGI server..."
exec gunicorn -b 0.0.0.0:5000 --access-logfile - --error-logfile - "app:create_app()"
