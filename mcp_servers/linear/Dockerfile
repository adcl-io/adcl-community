FROM python:3.11-slim

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY base_server.py .
COPY exceptions.py .
COPY linear_server.py .
COPY linear_client.py .
COPY oauth_manager.py .
COPY config.yaml .

# Expose port (default 7005, configurable via env)
EXPOSE 7005

# Health check to ensure MCP server is responding
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost',7005)); s.close()" || exit 1

# Run the linear server
CMD ["python", "linear_server.py"]
