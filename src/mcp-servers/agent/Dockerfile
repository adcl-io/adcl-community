FROM python:3.11-slim

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY base_server.py .
COPY agent_server.py .
COPY config_loader.py .
COPY config.yaml .

# Expose port (default 7000, configurable via env)
EXPOSE 7000

# Health check to ensure MCP server is responding
# Note: Assumes server has /health endpoint or is listening on port
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost',7000)); s.close()" || exit 1

# Run the agent server
CMD ["python", "agent_server.py"]
