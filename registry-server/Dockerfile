FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY registries/ ./registries/

# Health check to ensure process is running
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD pgrep -f "python server.py" || exit 1

CMD ["python", "server.py"]
