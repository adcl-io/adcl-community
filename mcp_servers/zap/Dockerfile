FROM ghcr.io/zaproxy/zaproxy:2.16.1

# Switch to root to install packages
USER root

# Install Python and dependencies
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy base server and ZAP server
WORKDIR /app
COPY base_server.py zap_server.py ./

# Switch back to zap user
USER zap

# Expose ports: MCP (7008), ZAP Proxy (8080), ZAP API (8090)
EXPOSE 7008 8080 8090

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:7008/health || exit 1

# Start MCP server (it will manage ZAP daemon)
CMD ["python3", "zap_server.py"]
