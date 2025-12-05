# ADCL Platform Distribution Strategy

## Overview

ADCL follows an **Open Core** model that leverages our modular MCP architecture to separate community and enterprise features without code obfuscation.

## Distribution Models Considered

### ❌ Python Bytecode Compilation (.pyc)
**Pros**: Easy to implement
**Cons**:
- Trivial to decompile with tools like `uncompyle6`
- No real IP protection
- Breaks debugging, harder to support
- Not suitable for serious IP protection

### ❌ Binary Compilation (PyInstaller, Nuitka)
**Pros**: Harder to reverse engineer than bytecode
**Cons**:
- Still reversible with effort
- Large binary sizes
- Platform-specific builds (Linux, macOS, Windows)
- Breaks Python's "inspect the source" philosophy
- Violates ADCL principle: "readable code"

### ❌ Code Obfuscation (pyarmor, etc.)
**Pros**: Makes code harder to read
**Cons**:
- Still reversible
- Performance overhead
- Breaks debugging and introspection
- Hostile to users
- Against open source community norms

### ✅ Open Core with MCP Separation (RECOMMENDED)

**Pros**:
- Leverages ADCL's modular architecture
- No obfuscation needed - just don't publish enterprise code
- Clear value proposition (basic features free, advanced features paid)
- Builds trust with community (transparent, inspectable code)
- Easy to support and debug
- Follows industry best practices (GitLab, Elastic, etc.)

**Cons**:
- Enterprise features are separate packages (but this is by design)

## Recommended Implementation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Public Distribution                       │
│                 (Open Source Community)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ADCL Platform Core                                         │
│  ├── Orchestrator (agent execution engine)                 │
│  ├── Frontend (web UI)                                     │
│  ├── Registry Server (package management)                  │
│  └── Community MCP Servers:                                │
│      ├── agent (basic LLM agent)                           │
│      ├── file_tools (file operations)                      │
│      ├── nmap_recon (network scanning)                     │
│      └── history (conversation storage)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Private Distribution                        │
│                   (Enterprise Only)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Enterprise MCP Packages (via private registry)             │
│  ├── advanced_recon (commercial scanning tools)            │
│  ├── vulnerability_db (commercial vuln databases)          │
│  ├── compliance (SOC2, HIPAA, PCI reports)                 │
│  ├── team_collaboration (multi-user, RBAC)                 │
│  ├── audit_logging (comprehensive audit trails)            │
│  ├── sso_integration (SAML, OIDC)                          │
│  └── priority_support (direct support channel)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Repository Structure

#### Public Repository (github.com/adcl-io/adcl-platform)

```bash
adcl-platform/
├── orchestrator/          # Core platform (open source)
├── frontend/             # Web UI (open source)
├── registry-server/      # Package registry (open source)
├── mcp_servers/          # Community MCPs (open source)
│   ├── agent/
│   ├── file_tools/
│   ├── nmap_recon/
│   └── history/
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── VERSION               # Version tracking
├── CHANGELOG.md          # Release notes
└── LICENSE               # Apache 2.0 / MIT
```

#### Private Registry (registry.adcl.io)

```bash
# Enterprise MCP packages hosted on private registry
# Requires authentication to download
adcl-enterprise/
└── packages/
    ├── advanced-recon-1.0.0.tar.gz
    ├── vulnerability-db-1.0.0.tar.gz
    ├── compliance-1.0.0.tar.gz
    ├── team-collaboration-1.0.0.tar.gz
    ├── audit-logging-1.0.0.tar.gz
    └── sso-integration-1.0.0.tar.gz
```

### Edition Configuration

#### Community Edition (.env)
```bash
ADCL_EDITION=community

# Community update URL (public S3)
COMMUNITY_UPDATE_URL=https://ai-releases.com/adcl-releases/releases/latest.json

# Community registry (public packages only)
REGISTRY_URL=http://registry:9000
```

#### Enterprise Edition (.env)
```bash
ADCL_EDITION=enterprise

# Enterprise license key
ADCL_LICENSE_KEY=ent_1234567890abcdef

# Enterprise registry (private packages)
REGISTRY_URL=https://registry.adcl.io
REGISTRY_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Enterprise update URL
ENTERPRISE_UPDATE_URL=https://registry.adcl.io/platform/releases/latest
```

## Package Distribution

### Community Edition Release

```bash
# 1. Build release archive (all source code)
./scripts/publish-release.sh 0.2.0

# Uploads to:
# https://ai-releases.com/adcl-releases/releases/v0.2.0/
# ├── VERSION
# ├── CHANGELOG.md
# ├── release.json
# └── adcl-platform-0.2.0.tar.gz (full source)

# 2. Users install via:
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash

# 3. Or clone from GitHub:
git clone https://github.com/adcl-io/adcl-platform.git
cd adcl-platform
docker compose up -d
```

### Enterprise Edition Distribution

```bash
# 1. Customer purchases enterprise license
# 2. Customer receives:
#    - License key: ADCL_LICENSE_KEY=ent_...
#    - Registry credentials: REGISTRY_AUTH_TOKEN=...
#    - Enterprise documentation

# 3. Customer installs community edition:
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash

# 4. Customer adds enterprise credentials to .env:
cat >> ~/.adcl/.env <<EOF
ADCL_EDITION=enterprise
ADCL_LICENSE_KEY=ent_1234567890abcdef
REGISTRY_URL=https://registry.adcl.io
REGISTRY_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
EOF

# 5. Install enterprise MCPs:
cd ~/.adcl
./scripts/install-enterprise-mcps.sh
```

## Feature Gating

### License Check in Backend

```python
# backend/app/services/license_service.py
class LicenseService:
    def __init__(self):
        self.edition = os.getenv("ADCL_EDITION", "community")
        self.license_key = os.getenv("ADCL_LICENSE_KEY")

    def check_feature(self, feature: str) -> bool:
        """Check if feature is available in current edition."""
        if self.edition == "community":
            return feature in COMMUNITY_FEATURES

        if self.edition == "enterprise":
            return self.validate_license() and feature in ENTERPRISE_FEATURES

        return False

    def validate_license(self) -> bool:
        """Validate enterprise license key."""
        if not self.license_key:
            return False

        # Call license server or validate JWT
        # Return True if valid, False otherwise
        return validate_license_key(self.license_key)

# Usage in API endpoints
@router.post("/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: str,
    license: LicenseService = Depends()
):
    # Check if agent requires enterprise
    agent_def = load_agent_definition(agent_id)

    if agent_def.get("enterprise_only"):
        if not license.check_feature("enterprise_agents"):
            raise HTTPException(
                status_code=403,
                detail="This agent requires ADCL Enterprise. Upgrade at https://adcl.io/pricing"
            )

    # Execute agent...
```

### MCP Server Availability

```json
// agent-definitions/advanced-recon.json
{
  "name": "advanced_recon",
  "version": "1.0.0",
  "enterprise_only": true,
  "mcp_servers": ["advanced_recon", "vulnerability_db"],
  "description": "Advanced reconnaissance with commercial vulnerability database",
  "upgrade_url": "https://adcl.io/pricing"
}
```

### Frontend Feature Gating

```jsx
// frontend/src/components/AgentCard.jsx
function AgentCard({ agent, edition }) {
  const isEnterpriseOnly = agent.enterprise_only;
  const hasAccess = edition === "enterprise" || !isEnterpriseOnly;

  return (
    <Card>
      <h3>{agent.name}</h3>
      {isEnterpriseOnly && <Badge>Enterprise</Badge>}

      {hasAccess ? (
        <Button onClick={() => runAgent(agent.id)}>
          Run Agent
        </Button>
      ) : (
        <Button variant="upgrade" href="https://adcl.io/pricing">
          Upgrade to Enterprise
        </Button>
      )}
    </Card>
  );
}
```

## License Validation

### Option 1: JWT-based (Offline)

```python
# License key is a JWT with claims:
# {
#   "edition": "enterprise",
#   "customer_id": "acme-corp",
#   "expires_at": "2026-12-31T23:59:59Z",
#   "features": ["advanced_recon", "compliance", "sso"]
# }

import jwt

def validate_license_key(license_key: str) -> dict:
    try:
        # Verify JWT signature with public key
        payload = jwt.decode(
            license_key,
            public_key,
            algorithms=["RS256"]
        )

        # Check expiration
        if datetime.utcnow() > datetime.fromisoformat(payload["expires_at"]):
            raise ValueError("License expired")

        return payload
    except Exception as e:
        logger.error(f"License validation failed: {e}")
        return None
```

### Option 2: Online Validation

```python
# Call license server for validation
async def validate_license_key(license_key: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://license.adcl.io/validate",
            json={"license_key": license_key},
            timeout=5.0
        )

        if response.status_code == 200:
            return response.json()

        return None
```

## Advantages of Open Core Model

### For ADCL Platform

1. **Natural Architecture Fit**
   - MCP servers are already independent modules
   - Registry system designed for package distribution
   - No code changes needed - just package differently

2. **Trust and Transparency**
   - Community can inspect all community code
   - No "what are they hiding?" concerns
   - Security researchers can audit the platform

3. **Community Growth**
   - Contributors can improve community features
   - Pull requests for core platform welcomed
   - Builds ecosystem around the platform

4. **Clear Value Proposition**
   - Community: Free, basic features, self-support
   - Enterprise: Advanced features, SLA, support, compliance

5. **Easy Upgrades**
   - Community → Enterprise is just adding packages
   - No reinstallation needed
   - Can trial enterprise features easily

### For Customers

1. **Try Before You Buy**
   - Start with community edition
   - Evaluate platform with real workflows
   - Upgrade when you need advanced features

2. **No Lock-in**
   - All core platform is open source
   - Can fork if needed
   - Not dependent on proprietary code

3. **Transparent Pricing**
   - Clear what's included in each edition
   - No hidden features or surprise costs
   - Can see source code of what you're using

## Example Enterprise Features

### Advanced Reconnaissance MCP
- Integration with Shodan, Censys, VirusTotal APIs
- Historical scan data and trends
- Automated attack surface monitoring

### Vulnerability Database MCP
- Commercial vulnerability databases (NIST NVD+)
- Exploit databases and proof-of-concepts
- Risk scoring and prioritization

### Compliance MCP
- SOC2, HIPAA, PCI-DSS report generation
- Automated evidence collection
- Audit trail export

### Team Collaboration MCP
- Multi-user support with RBAC
- Shared workflows and agents
- Team chat and annotations

### Audit Logging MCP
- Comprehensive audit trails
- Immutable log storage
- SIEM integration

### SSO Integration MCP
- SAML 2.0 and OIDC support
- Active Directory / LDAP
- MFA enforcement

## Marketing Benefits

### Positioning

**Community Edition**
- "Professional-grade security automation for everyone"
- "Free and open source"
- "No vendor lock-in"

**Enterprise Edition**
- "Battle-tested in production"
- "Commercial-grade tools and databases"
- "White-glove support and SLA"

### Conversion Funnel

1. **Awareness**: Blog posts, tutorials, GitHub stars
2. **Trial**: Download community edition, try workflows
3. **Engagement**: Use for real projects, join community
4. **Qualification**: Need advanced features or support
5. **Conversion**: Purchase enterprise license
6. **Expansion**: Add more seats, features, support tiers

## Implementation Checklist

- [x] Core platform supports edition configuration
- [x] VERSION file includes edition field
- [x] Backend VersionService supports enterprise URLs
- [ ] LicenseService for feature gating
- [ ] Frontend edition detection and upgrade prompts
- [ ] Enterprise MCP packages (separate repo)
- [ ] Private package registry setup
- [ ] License key generation system
- [ ] Documentation for both editions
- [ ] Marketing site with clear pricing

## Conclusion

For ADCL Platform, **Open Core with MCP Separation** is the best approach because:

1. Leverages the existing modular architecture
2. No obfuscation needed - clear separation of editions
3. Builds trust with transparent community code
4. Natural upgrade path from community to enterprise
5. Industry-proven model (used by GitLab, Elastic, MongoDB, etc.)

The key insight: **Don't hide the code, hide the enterprise packages**. This aligns perfectly with ADCL's philosophy of transparent, inspectable systems.
