FROM kalilinux/kali-rolling:latest

# Set working directory
WORKDIR /app

# Update and install basic tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Kali penetration testing tools
RUN apt-get update && apt-get install -y \
    nmap \
    nikto \
    dirb \
    sqlmap \
    metasploit-framework \
    hydra \
    wpscan \
    dnsenum \
    dnsutils \
    whois \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Sublist3r via pip
RUN pip3 install --break-system-packages --no-cache-dir sublist3r requests dnspython argparse

# Copy Python requirements
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY base_server.py .
COPY kali_server.py .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 7005

# Health check to ensure MCP server is responding
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost',7005)); s.close()" || exit 1

# Run the MCP server
CMD ["python3", "kali_server.py"]
