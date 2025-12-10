# Registry Guide

Learn about ADCL's package management system for installing teams, triggers, and MCPs.

---

## Table of Contents

1. [What is the Registry?](#what-is-the-registry)
2. [How the Registry Works](#how-the-registry-works)
3. [Browsing Packages](#browsing-packages)
4. [Installing Packages](#installing-packages)
5. [Managing Registries](#managing-registries)
6. [Creating Packages](#creating-packages)
7. [Publishing Packages](#publishing-packages)
8. [Best Practices](#best-practices)

---

## What is the Registry?

The **ADCL Registry** is a package management system similar to Yum/APT for Linux or npm for Node.js. It allows you to:

- **Browse** available packages (teams, triggers, MCPs)
- **Install** packages with one click
- **Manage** multiple registry sources
- **Publish** your own packages
- **Version** package releases

### Package Types

**Teams**: Multi-agent configurations
```
Example: Security Analysis Team
  - Pre-configured agents with roles
  - Specialized tools per role
  - Collaborative workflow
```

**Triggers**: Automation configurations
```
Example: Nightly Security Scan Trigger
  - Schedule: Daily at 2 AM
  - Executes: Security scan workflow
  - Notifications on completion
```

**MCPs**: Tool servers (future feature)
```
Example: Custom API Integration MCP
  - Tools for external API
  - Docker container
  - Configuration templates
```

---

## How the Registry Works

### Architecture

```
┌──────────────────────────────────────────────┐
│  ADCL Platform                               │
│  ┌────────────┐                              │
│  │ Registry   │ Queries registries           │
│  │ Client     │─────────────────────┐        │
│  └────────────┘                     │        │
└─────────────────────────────────────┼────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────┐
│  Registry Server (Port 9000)                 │
│  ┌────────────────────────────────┐          │
│  │ Package Repository             │          │
│  │ - Teams                        │          │
│  │ - Triggers                     │          │
│  │ - MCPs                         │          │
│  └────────────────────────────────┘          │
└──────────────────────────────────────────────┘
```

### Registry Configuration

Registries are configured in `registries.conf` (INI format):

```ini
[official]
name=ADCL Official Repository
baseurl=http://localhost:9000
enabled=1
gpgcheck=0
priority=10

[community]
name=Community Packages
baseurl=http://community.adcl.io
enabled=1
gpgcheck=0
priority=20

[custom]
name=Company Internal Registry
baseurl=http://registry.internal.company.com
enabled=1
gpgcheck=1
gpgkey=http://registry.internal.company.com/gpg-key.asc
priority=30
```

**Priority**: Lower number = higher priority (like Yum)

---

## Browsing Packages

### Via Web UI

**Step 1**: Navigate to Registry
```
http://localhost:3000 → Registry
```

**Step 2**: Browse Categories
```
Tabs:
  - Teams: Pre-configured agent teams
  - Triggers: Automation configurations
  - MCPs: Tool servers (coming soon)
```

**Step 3**: View Package Details
```
Click on package to view:
  - Description
  - Version
  - Author
  - Dependencies
  - Installation instructions
  - Preview (team.json, trigger config, etc.)
```

### Via API

**List All Packages**:
```bash
curl http://localhost:8000/registries/packages
```

**List Specific Type**:
```bash
# Teams only
curl http://localhost:8000/registries/packages?type=team

# Triggers only
curl http://localhost:8000/registries/packages?type=trigger
```

**Search Packages**:
```bash
curl "http://localhost:8000/registries/packages?search=security"
```

**Get Package Details**:
```bash
curl http://localhost:8000/registries/packages/security_analysis_team
```

**Response**:
```json
{
  "name": "security_analysis_team",
  "version": "1.0.0",
  "type": "team",
  "description": "Complete security assessment workflow",
  "author": "ADCL Team",
  "registry": "official",
  "metadata": {
    "tags": ["security", "network", "analysis"],
    "dependencies": [],
    "size": "12KB"
  },
  "preview": {
    "agents": [
      {"role": "scanner", "mcp_servers": ["nmap_recon"]},
      {"role": "analyst", "mcp_servers": ["agent", "file_tools"]},
      {"role": "reporter", "mcp_servers": ["file_tools"]}
    ]
  }
}
```

---

## Installing Packages

### Install Team

**Via UI**:
```
1. Go to Registry → Teams
2. Find "Security Analysis Team"
3. Click "Install"
4. Wait for installation
5. Team appears in Teams page
6. Use immediately in Playground
```

**Via API**:
```bash
curl -X POST http://localhost:8000/registries/install \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "security_analysis_team",
    "version": "1.0.0"
  }'
```

**Installation Process**:
```
1. Download package from registry
2. Validate package signature (if gpgcheck=1)
3. Check dependencies
4. Extract files to:
   - Teams: agent-teams/
   - Agents: agent-definitions/
5. Register team in platform
6. Team available for use
```

### Install Trigger

**Via UI**:
```
1. Go to Registry → Triggers
2. Find "Nightly Security Scan"
3. Click "Install"
4. Configure parameters:
   - Schedule time
   - Target network
   - Notification emails
5. Enable trigger
```

**Via API**:
```bash
curl -X POST http://localhost:8000/registries/install \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "nightly_security_scan",
    "version": "1.0.0",
    "config": {
      "schedule": "0 2 * * *",
      "target": "192.168.1.0/24",
      "notifications": ["ops@company.com"]
    }
  }'
```

### Package Dependencies

Some packages have dependencies:

```json
{
  "name": "advanced_security_team",
  "dependencies": [
    {"name": "kali_mcp", "version": ">=1.0.0"},
    {"name": "nmap_recon", "version": ">=2.0.0"}
  ]
}
```

**Installation** automatic installs dependencies:
```
Installing: advanced_security_team
  → Checking dependencies...
  → Installing: kali_mcp (1.0.0)
  → Installing: nmap_recon (2.1.0)
  → Installing: advanced_security_team (1.0.0)
✓ Installation complete
```

---

## Managing Registries

### Adding a Registry

**Edit registries.conf**:
```bash
cat >> registries.conf <<EOF
[myregistry]
name=My Custom Registry
baseurl=http://registry.example.com
enabled=1
gpgcheck=0
priority=25
EOF
```

**Restart platform**:
```bash
./clean-restart.sh
```

**Verify**:
```bash
curl http://localhost:8000/registries
```

### Disabling a Registry

**Edit registries.conf**:
```ini
[community]
name=Community Packages
baseurl=http://community.adcl.io
enabled=0  # Disabled
gpgcheck=0
priority=20
```

### Registry Priority

Lower priority number = higher precedence:

```ini
[official]
priority=10  # Highest

[company-internal]
priority=20  # Medium

[community]
priority=30  # Lowest
```

If same package exists in multiple registries, highest priority wins.

### GPG Signature Verification

**Enable GPG checking**:
```ini
[secure-registry]
name=Secure Registry
baseurl=http://secure.registry.com
enabled=1
gpgcheck=1  # Enable signature verification
gpgkey=http://secure.registry.com/gpg-key.asc
```

**Platform verifies**:
1. Download package
2. Download signature (.sig file)
3. Verify with GPG key
4. Only install if valid

---

## Creating Packages

### Team Package Structure

```
security_analysis_team-1.0.0/
├── metadata.json           # Package metadata
├── team.json              # Team definition
├── agents/                # Agent definitions
│   ├── scanner.json
│   ├── analyst.json
│   └── reporter.json
├── README.md             # Documentation
└── LICENSE               # License file
```

### Package Metadata

**metadata.json**:
```json
{
  "name": "security_analysis_team",
  "version": "1.0.0",
  "type": "team",
  "description": "Complete security assessment workflow with scanner, analyst, and reporter agents",
  "author": "ADCL Team",
  "email": "support@adcl.io",
  "license": "MIT",
  "homepage": "https://github.com/adcl-io/security-analysis-team",
  "tags": ["security", "network", "analysis"],
  "dependencies": [
    {
      "name": "nmap_recon",
      "version": ">=1.0.0",
      "type": "mcp"
    }
  ],
  "changelog": {
    "1.0.0": "Initial release",
    "0.9.0": "Beta release"
  }
}
```

### Team Definition

**team.json**:
```json
{
  "name": "security_analysis_team",
  "version": "1.0.0",
  "description": "Complete security assessment",
  "agents": [
    {
      "role": "scanner",
      "agent_id": "network_scanner",
      "mcp_servers": ["nmap_recon"],
      "persona": "You scan networks and identify hosts..."
    },
    {
      "role": "analyst",
      "agent_id": "security_analyst",
      "mcp_servers": ["agent", "file_tools"],
      "persona": "You analyze scan results..."
    },
    {
      "role": "reporter",
      "agent_id": "report_writer",
      "mcp_servers": ["file_tools"],
      "persona": "You create security reports..."
    }
  ]
}
```

### Package README

**README.md**:
```markdown
# Security Analysis Team

Complete security assessment workflow with three specialized agents.

## Description

This team performs comprehensive network security assessments:

1. **Scanner**: Discovers hosts and services
2. **Analyst**: Identifies vulnerabilities and risks
3. **Reporter**: Creates formatted security reports

## Requirements

- MCP: `nmap_recon` >= 1.0.0
- Network: Access to scan targets

## Usage

1. Install the package
2. Go to Playground
3. Select "Security Analysis Team"
4. Task: "Scan 192.168.1.0/24 and create security report"

## Configuration

Customize scanning behavior in `.env`:
```bash
DEFAULT_SCAN_NETWORK=192.168.1.0/24
```

## Examples

**Example 1**: Basic scan
```
Task: "Scan my network"
Output: Security report in /workspace/
```

**Example 2**: Specific target
```
Task: "Perform deep security analysis of 10.0.1.0/24"
Output: Detailed vulnerability assessment
```

## License

MIT
```

---

## Publishing Packages

### To Official Registry

**1. Prepare Package**:
```bash
# Create package directory
mkdir security_analysis_team-1.0.0
cd security_analysis_team-1.0.0

# Add files
cp ../agent-teams/security_analysis_team.json team.json
cp -r ../agent-definitions/scanner.json agents/
# ... add other files

# Create metadata
cat > metadata.json <<EOF
{
  "name": "security_analysis_team",
  "version": "1.0.0",
  ...
}
EOF
```

**2. Create Archive**:
```bash
tar -czf security_analysis_team-1.0.0.tar.gz \
  security_analysis_team-1.0.0/
```

**3. Sign (if GPG enabled)**:
```bash
gpg --detach-sign --armor \
  security_analysis_team-1.0.0.tar.gz
```

**4. Submit to Registry**:
```bash
curl -X POST http://registry.adcl.io/publish \
  -F "package=@security_analysis_team-1.0.0.tar.gz" \
  -F "signature=@security_analysis_team-1.0.0.tar.gz.asc" \
  -H "Authorization: Bearer $REGISTRY_TOKEN"
```

### To Private Registry

**1. Set up private registry server** (copy of ADCL registry server)

**2. Configure in registries.conf**:
```ini
[company]
name=Company Registry
baseurl=http://registry.company.com
enabled=1
priority=15
```

**3. Publish package**:
```bash
curl -X POST http://registry.company.com/publish \
  -F "package=@my-package-1.0.0.tar.gz" \
  -H "Authorization: Bearer $COMPANY_TOKEN"
```

---

## Best Practices

### 1. Semantic Versioning

Follow semver (MAJOR.MINOR.PATCH):

```
1.0.0 → Initial release
1.0.1 → Bug fix (backward compatible)
1.1.0 → New feature (backward compatible)
2.0.0 → Breaking change
```

### 2. Complete Metadata

**Do**:
```json
{
  "name": "security_analysis_team",
  "version": "1.0.0",
  "description": "Detailed description...",
  "author": "Company Name",
  "tags": ["security", "network"],
  "dependencies": [],
  "changelog": {...}
}
```

**Don't**:
```json
{
  "name": "team",
  "version": "1.0.0"
}
```

### 3. Clear Documentation

Include comprehensive README with:
- Description
- Requirements
- Installation instructions
- Usage examples
- Configuration options
- Troubleshooting

### 4. Test Before Publishing

**Test locally**:
```bash
# Install package from local file
./install-package.sh ./my-package-1.0.0.tar.gz

# Test functionality
# Use in Playground or API
# Verify all features work
```

### 5. Specify Dependencies

**Do**:
```json
{
  "dependencies": [
    {"name": "nmap_recon", "version": ">=1.0.0"}
  ]
}
```

**Don't**:
```json
{
  "dependencies": []  // Missing required MCP
}
```

---

## Troubleshooting

### Package Not Found

**Symptom**: "Package security_team not found"

**Solutions**:
```bash
# Refresh registry cache
curl -X POST http://localhost:8000/registries/refresh

# Check registry is enabled
cat registries.conf

# Verify registry server is up
curl http://localhost:9000/health
```

### Installation Failed

**Symptom**: "Failed to install package"

**Solutions**:
```bash
# Check logs
docker-compose logs registry

# Verify dependencies available
curl http://localhost:8000/registries/packages

# Check disk space
df -h

# View detailed error
cat logs/registry-*.log
```

### Signature Verification Failed

**Symptom**: "GPG signature verification failed"

**Solutions**:
```bash
# Import GPG key
gpg --import gpg-key.asc

# Disable verification temporarily
# Edit registries.conf: gpgcheck=0

# Verify signature manually
gpg --verify package.tar.gz.sig package.tar.gz
```

---

## Next Steps

- **[Teams Guide](Teams-Guide)** - Create teams to package
- **[Triggers Guide](Triggers-Guide)** - Create triggers to package
- **[MCP Servers Guide](MCP-Servers-Guide)** - Create MCPs to package

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
