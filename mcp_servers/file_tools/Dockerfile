FROM python:3.11-slim

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY base_server.py .
COPY file_server.py .

# Expose port (default 7002, configurable via env)
EXPOSE 7002

# Health check to ensure MCP server is responding
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost',7002)); s.close()" || exit 1

# Run the file tools server
CMD ["python", "file_server.py"]
