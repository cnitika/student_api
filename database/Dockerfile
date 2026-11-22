FROM mysql:8.0

# Copy SQL initialization script into the container entrypoint directory
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
