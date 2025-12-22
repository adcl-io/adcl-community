# ZAP MCP Server

OWASP ZAP security scanner exposed as an MCP server.

## Architecture

Single container with:
- MCP server (FastAPI on port 7008)
- ZAP daemon (proxy on 8080, API on 8090)

## Tools

- `start_proxy(port)` - Start ZAP proxy daemon
- `get_urls()` - Query discovered endpoints from sitemap
- `active_scan(target, scan_policy)` - Run vulnerability scan
- `get_scan_status(scan_id)` - Check scan progress
- `get_alerts(risk_level)` - Query vulnerability findings
- `generate_report(format)` - Export security report

## Usage

```bash
# Build
docker build -t mcp-zap:1.0.0 .

# Run
docker run -p 7008:7008 -p 8080:8080 -p 8090:8090 \
  -e ALLOWED_SCAN_TARGETS="http://localhost:*" \
  mcp-zap:1.0.0
```

## Security

- Target whitelist via `ALLOWED_SCAN_TARGETS` environment variable
- Input validation on scan_policy parameter
- Detection-only scanning (no data exfiltration)

## Dependencies

- ZAP 2.16.1
- python-owasp-zap-v2.4==0.0.21
- FastAPI, uvicorn, requests
