FROM python:3.11-slim

# Install nmap
RUN apt-get update && \
    apt-get install -y nmap && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY base_server.py .
COPY nmap_server.py .

# Expose port (default 7003, configurable via env)
EXPOSE 7003

# Health check to ensure MCP server is responding
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost',7003)); s.close()" || exit 1

# Run the nmap recon server
CMD ["python", "nmap_server.py"]
