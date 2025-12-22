FROM mcr.microsoft.com/playwright/mcp:latest

# Expose MCP port
EXPOSE 7007

# Start Playwright MCP with proxy server and allow all hosts
CMD ["--headless", "--port", "7007", "--host", "0.0.0.0", "--allowed-hosts", "*", "--proxy-server=http://mcp-zap:8080"]
