# Kali Linux MCP Server

Penetration testing tools for authorized security assessments.

**⚠️ DEFENSIVE USE ONLY** - For authorized penetration testing and security assessments on systems you own or have explicit permission to test.

## Overview

The Kali MCP provides access to industry-standard penetration testing tools from Kali Linux through the ADCL MCP protocol. This allows agents to perform comprehensive security assessments using tools like Nikto, SQLMap, Metasploit, and more.

## Available Tools

### 1. `nikto_scan`
Web vulnerability scanner that checks for dangerous files, outdated servers, and specific problems.

**Parameters:**
- `target` (required): Target URL (e.g., http://example.com)
- `port` (optional): Target port (default: 80)
- `ssl` (optional): Use SSL/HTTPS

**Example:**
```json
{
  "target": "http://192.168.1.100",
  "port": "8080",
  "ssl": false
}
```

### 2. `dirb_scan`
Directory and file brute forcing tool to discover hidden web content.

**Parameters:**
- `target` (required): Target URL
- `wordlist` (optional): Wordlist to use (common, big, small)

**Example:**
```json
{
  "target": "http://example.com",
  "wordlist": "common"
}
```

### 3. `sqlmap_scan`
Automated SQL injection detection and exploitation tool.

**Parameters:**
- `target` (required): Target URL with parameter (e.g., http://example.com/page?id=1)
- `level` (optional): Test level 1-5 (default: 1)
- `risk` (optional): Risk level 1-3 (default: 1)

**Example:**
```json
{
  "target": "http://example.com/product.php?id=5",
  "level": "2",
  "risk": "1"
}
```

### 4. `metasploit_search`
Search Metasploit Framework for exploits and modules.

**Parameters:**
- `query` (required): Search term (software/CVE/service)
- `type` (optional): Module type (exploit, auxiliary, payload)

**Example:**
```json
{
  "query": "apache struts",
  "type": "exploit"
}
```

### 5. `hydra_bruteforce`
Fast network authentication cracker.

**Parameters:**
- `target` (required): Target IP or hostname
- `service` (required): Service to attack (ssh, ftp, http-get, etc.)
- `username` (required): Username or path to username list
- `password_list` (required): Path to password wordlist

**Example:**
```json
{
  "target": "192.168.1.100",
  "service": "ssh",
  "username": "admin",
  "password_list": "/usr/share/wordlists/rockyou.txt"
}
```

### 6. `wpscan`
WordPress vulnerability scanner.

**Parameters:**
- `target` (required): Target WordPress URL
- `enumerate` (optional): What to enumerate (vp=plugins, vt=themes, u=users)

**Example:**
```json
{
  "target": "http://wordpress.example.com",
  "enumerate": "vp,u"
}
```

### 7. `dns_enum`
DNS enumeration to discover nameservers, mail servers, and hosts.

**Parameters:**
- `domain` (required): Target domain

**Example:**
```json
{
  "domain": "example.com"
}
```

### 8. `subdomain_enum`
Subdomain discovery using Sublist3r.

**Parameters:**
- `domain` (required): Target domain
- `bruteforce` (optional): Enable brute force (slower but more thorough)

**Example:**
```json
{
  "domain": "example.com",
  "bruteforce": false
}
```

## Architecture

The Kali MCP follows the ADCL platform architecture:

- **Base Image**: `kalilinux/kali-rolling:latest`
- **Network Mode**: Host (required for raw packet manipulation)
- **Port**: 7005
- **Capabilities**: NET_RAW, NET_ADMIN (required for certain scans)

## Deployment

The MCP is automatically deployed via the orchestrator when included in `AUTO_INSTALL_MCPS`.

### Manual Deployment

```bash
# Build image
docker build -t mcp-kali:1.0.0 .

# Run container
docker run -d \
  --name mcp-kali \
  --network host \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -e KALI_PORT=7005 \
  mcp-kali:1.0.0
```

## Security Considerations

### Authorization Required
- Only use on systems you own or have written permission to test
- Unauthorized penetration testing is illegal
- Always follow responsible disclosure practices

### Ethical Guidelines
1. **Obtain explicit written permission** before testing any system
2. **Define scope clearly** - know what's in and out of scope
3. **Maintain confidentiality** of discovered vulnerabilities
4. **Report findings responsibly** to system owners
5. **Do not cause harm** - avoid destructive tests unless authorized

### Legal Notice
Misuse of penetration testing tools can result in:
- Criminal prosecution under computer fraud laws
- Civil liability for damages
- Termination of service agreements
- Professional sanctions

## Integration

### Agent Teams

Create specialized penetration testing teams:

```json
{
  "name": "PenTest Team",
  "available_mcps": ["kali", "nmap_recon", "agent"],
  "agents": [
    {
      "agent_id": "recon-specialist",
      "mcp_access": ["nmap_recon", "kali"]
    },
    {
      "agent_id": "web-app-tester",
      "mcp_access": ["kali", "agent"]
    }
  ]
}
```

### Example Workflow

```json
{
  "name": "Web Application Security Assessment",
  "steps": [
    {
      "tool": "nikto_scan",
      "target": "http://target-app.com"
    },
    {
      "tool": "dirb_scan",
      "target": "http://target-app.com",
      "wordlist": "big"
    },
    {
      "tool": "wpscan",
      "target": "http://target-app.com",
      "enumerate": "vp,vt,u"
    }
  ]
}
```

## Included Tools

The Kali MCP container includes:

- **Nikto**: Web server scanner
- **DIRB**: Web content scanner
- **SQLMap**: SQL injection tool
- **Metasploit Framework**: Exploitation framework
- **Hydra**: Network logon cracker
- **WPScan**: WordPress scanner
- **dnsenum**: DNS enumeration
- **Sublist3r**: Subdomain discovery
- **Nmap**: Network scanner (already in nmap_recon MCP)

## Logs

Logs are written to `/app/logs/` inside the container, mounted to `./logs/kali/` on the host.

## Health Check

```bash
curl http://localhost:7005/health
```

## Troubleshooting

### Container won't start
- Ensure host networking is available
- Check that port 7005 is not in use
- Verify capabilities are granted (NET_RAW, NET_ADMIN)

### Tools not working
- Some tools require root privileges
- Verify target is reachable
- Check firewall rules
- Ensure wordlists exist if specified

### Permission denied errors
- Container may need additional capabilities
- Some scans require specific network configuration
- Check SELinux/AppArmor policies

## References

- [Kali Linux Official](https://www.kali.org/)
- [ADCL Platform Documentation](../../docs/)
- [MCP Protocol Specification](../../docs/mcp-protocol.md)
- [Penetration Testing Execution Standard](http://www.pentest-standard.org/)

## License

MIT License - See repository root for details

## Support

For issues specific to the Kali MCP:
- Check logs in `./logs/kali/`
- Verify tool installation: `docker exec mcp-kali which nikto`
- Test tools manually: `docker exec mcp-kali nikto -Version`

---

**Remember**: With great power comes great responsibility. Use these tools ethically and legally.
