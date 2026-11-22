FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root application user and group
RUN groupadd -r appuser && useradd -r -g appuser -u 10001 -d /app -s /sbin/nologin appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set correct permissions for non-root user and entrypoint script
RUN chown -R appuser:appuser /app && chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 5000

# Health check using standard Python library (no curl needed in slim image)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health').getcode() == 200 else 1)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
