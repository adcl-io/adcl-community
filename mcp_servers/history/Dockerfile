FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks (ADCL: Unix philosophy - use standard tools)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all server files (includes base_server.py and history modules)
COPY *.py ./

# Create storage directory
RUN mkdir -p /app/volumes/conversations

# Health check (ADCL: Use curl instead of Python for simplicity)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7004/health || exit 1

# Run server
CMD ["python", "history_server.py"]
