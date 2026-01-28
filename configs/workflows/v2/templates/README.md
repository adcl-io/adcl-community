# Workflow Templates

Pre-built workflow templates for common security testing scenarios.

## Template Structure

Each template is a JSON file with the following schema:

```json
{
  "template_id": "unique-identifier",
  "name": "Human-Readable Name",
  "description": "Brief description of what this workflow does",
  "category": "pentesting|web|api|automation",
  "tags": ["tag1", "tag2"],
  "version": "1.0.0",
  "author": "adcl.io",
  "workflow": {
    // Full workflow V2 definition
    "workflow_id": "generated-from-template",
    "version": "2.0",
    "nodes": [...],
    "edges": [...]
  }
}
```

## Categories

- **pentesting**: Network reconnaissance and penetration testing
- **web**: Web application security testing
- **api**: API security testing
- **automation**: Automated workflows and reporting

## Available Templates

1. **basic-recon.json** - Basic network reconnaissance (Ping → Nmap)
2. **full-red-team-chain.json** - Complete attack chain (Recon → Discovery → Vuln → Exploit)
3. **web-app-audit.json** - Web application security audit (Scan → SQLi → XSS)
4. **conditional-exploitation.json** - Conditional exploit workflow (If vulnerable → Exploit)
5. **parallel-scan.json** - Multiple scanners in parallel → Merge results
6. **automated-reporting.json** - Scan → Report → Email workflow
7. **api-security-test.json** - API security testing workflow

## Usage

Templates can be loaded into the workflow builder via the Template Library UI or programmatically:

```javascript
import template from './templates/basic-recon.json';

// Load template into workflow
loadTemplate(template);
```
