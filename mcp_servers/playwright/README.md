# Playwright MCP Server

Microsoft's Playwright browser automation exposed as an MCP server.

## Architecture

Uses upstream `@playwright/mcp` package with native HTTP support.

## Configuration

- Port: 7007
- Headless mode enabled
- Proxy: Routes all traffic through ZAP (http://zap:8080)

## Tools

Provided by upstream @playwright/mcp:
- `browser_navigate(url)` - Navigate to URL
- `browser_click(selector)` - Click element
- `browser_type(selector, text)` - Type text
- `browser_fill_form(fields)` - Fill multiple fields
- `browser_wait_for(condition)` - Wait for conditions
- `browser_network_requests()` - Get network activity
- `browser_snapshot()` - Get accessibility snapshot
- `browser_take_screenshot()` - Take screenshot

## Usage

```bash
# Build
docker build -t mcp-playwright:1.0.0 .

# Run
docker run -p 7007:7007 --network mcp-network mcp-playwright:1.0.0
```

## Notes

- All browser traffic automatically routed through ZAP proxy
- No custom code needed (uses upstream implementation)
- Headless mode for better Docker performance
