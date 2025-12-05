IMPLEMENTATION SPECIFICATION: GPG Package Signing for Agent Registry (Complete)

Context
Building a YUM-style package signing system for AI agent registry. The system distributes three types of packages:

Agents: Individual AI agent configurations
MCPs: MCP server configurations
Teams: Compositions that orchestrate multiple agents and MCPs

All packages must be cryptographically signed by publishers and verified by users.
Architecture Decisions

Model: YUM-style (individual package signatures, not repository-level)
Format: Detached GPG signatures (.asc files alongside configs)
Trust: Users explicitly trust publisher public keys
Storage: Filesystem-based registry with publishers/, agents/, mcps/, teams/ directories
Verification: Enabled by default, transitive verification for dependencies
Package Types: agent, mcp, team (all use same signing infrastructure)


Directory Structure
registry/
  publishers/
    {publisher_id}/
      pubkey.asc              # Publisher's public GPG key
      metadata.json           # Publisher info (name, email, created)
      
  agents/
    {agent_name}/
      {version}/
        agent.json            # Agent configuration
        agent.json.asc        # Detached GPG signature
        metadata.json         # Package metadata
        
  mcps/
    {mcp_name}/
      {version}/
        mcp.json              # MCP server configuration
        mcp.json.asc          # Detached GPG signature
        metadata.json         # Package metadata
        
  teams/
    {team_name}/
      {version}/
        team.json             # Team composition (references agents/mcps)
        team.json.asc         # Detached GPG signature
        metadata.json         # Package metadata

~/.agent-cli/
  config.json                 # User config with trusted publishers
  keyring/                    # Imported publisher keys (GPG home dir)

Implementation Requirements
1. GPG Wrapper Module (src/signing/gpg.py)
Create Python wrapper for GPG operations:
Functions needed:
pythondef generate_keypair(email: str, name: str) -> str:
    """Creates new GPG key, returns key_id"""
    
def sign_file(filepath: str, key_id: str) -> str:
    """Creates detached signature (.asc), returns signature path"""
    
def verify_signature(filepath: str, signature_path: str, keyring_dir: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)"""
    
def export_public_key(key_id: str) -> str:
    """Returns public key as ASCII-armored string"""
    
def import_public_key(key_data: str, keyring_dir: str) -> str:
    """Imports key to user keyring, returns key_id"""
    
def get_signature_info(signature_path: str) -> dict:
    """Returns {key_id, timestamp, signer_email}"""
Use: python-gnupg library for GPG operations
Error handling:

Raise GPGNotFoundError if GPG not installed
Raise InvalidSignatureError with details on verification failure
Raise KeyNotFoundError if signing key missing


2. Package Type Definitions (src/registry/package_types.py)
Base Package Class:
pythonclass Package:
    type: str  # 'agent', 'mcp', or 'team'
    name: str
    version: str
    publisher: str
    config: dict  # The actual JSON content
    dependencies: list[Dependency]  # For teams
    
class Dependency:
    type: str  # 'agent' or 'mcp'
    name: str
    version: str  # Exact version required
Team Configuration Format (team.json):
json{
  "name": "pentest",
  "description": "Autonomous penetration testing team",
  "version": "1.0.0",
  "publisher": "jason@adcl",
  "dependencies": {
    "agents": [
      {"name": "security-analyst", "version": "1.0.0"},
      {"name": "reporter", "version": "1.2.0"}
    ],
    "mcps": [
      {"name": "nmap_recon", "version": "2.1.0"},
      {"name": "file_tools", "version": "1.0.0"}
    ]
  },
  "workflow": {
    // Team orchestration config
  }
}

3. CLI Commands (src/cli/signing_commands.py)
agent-cli keygen
bashagent-cli keygen --email jason@adcl --name "Jason Cafarelli"

Generates GPG keypair
Exports public key to registry/publishers/{email}/pubkey.asc
Creates publisher metadata.json
Prints: "Key generated. Users can trust you with: agent-cli trust jason@adcl"

agent-cli sign <filepath> --type [agent|mcp|team]
bashagent-cli sign pentest/security-analyst.json --type agent
agent-cli sign teams/pentest.json --type team

Signs given file with user's GPG key
Creates {filepath}.asc detached signature
Validates package structure before signing
Updates/creates metadata.json

agent-cli publish <package_path> --type [agent|mcp|team] --version X.Y.Z
bashagent-cli publish agents/security-analyst/ --type agent --version 1.0.0
agent-cli publish teams/pentest/ --type team --version 1.0.0

Validates package has signature
Validates all dependencies exist (for teams)
Copies package + signature to registry in correct directory
Updates registry index

agent-cli trust <publisher_id>
bashagent-cli trust jason@adcl

Downloads publisher's public key from registry
Shows key fingerprint and asks for confirmation
Imports to user's keyring (~/.agent-cli/keyring/)
Adds to trusted publishers list in config
Prints: "Publisher jason@adcl is now trusted"

agent-cli pull <package_type>/<package_name> [--version X.Y.Z] [--no-verify]
bashagent-cli pull agent/security-analyst --version 1.0.0
agent-cli pull team/pentest  # Latest version
agent-cli pull mcp/nmap_recon --no-verify  # Skip verification

Downloads package from registry
Verifies signature against trusted keyring (unless --no-verify)
For teams: Recursively verifies all dependencies
Fails with clear error if any signature invalid or publisher untrusted
Installs package locally
Returns dependency tree and verification status

agent-cli verify <local_package_path>
bashagent-cli verify ./teams/pentest/

Verifies locally installed package
Checks all dependencies if team
Reports verification status without reinstalling

agent-cli list-publishers [--trusted-only]
bashagent-cli list-publishers
agent-cli list-publishers --trusted-only

Lists known publishers from registry
Shows trust status for each


4. Dependency Verification (src/signing/dependency_verifier.py)
Core logic:
pythondef verify_package_tree(package: Package, keyring_dir: str) -> VerificationResult:
    """
    Recursively verifies package and all dependencies.
    Returns detailed verification result with any failures.
    """
    # 1. Verify package signature
    # 2. If team: verify each agent dependency
    # 3. If team: verify each MCP dependency
    # 4. Return aggregate result
    
class VerificationResult:
    success: bool
    package: str
    verified: list[str]  # Successfully verified packages
    failed: list[tuple[str, str]]  # (package, reason)
    untrusted: list[str]  # Packages from untrusted publishers
Verification rules:

All packages in dependency tree must be signed
All publishers in dependency tree must be trusted
Signature must match package content (checksum verification)
Fail-fast: Stop on first verification failure


5. Registry API Endpoints (src/registry/signing_routes.py)
POST /packages/publish
json{
  "type": "agent|mcp|team",
  "name": "security-analyst",
  "version": "1.0.0",
  "content": "base64_encoded_json",
  "signature": "base64_encoded_asc",
  "publisher": "jason@adcl"
}

Verify signature is valid before accepting
For teams: validate all dependencies exist in registry
Store in correct directory structure
Return success/failure with details

GET /packages/{type}/{name}/{version}
json{
  "type": "agent",
  "name": "security-analyst",
  "version": "1.0.0",
  "content": {...},
  "signature": "...",
  "publisher": "jason@adcl",
  "metadata": {...}
}
GET /packages/{type}/{name}/versions

List all versions of a package

GET /publishers/{publisher_id}/key

Return publisher's public key (ASCII-armored)
Used by agent-cli trust

GET /publishers/{publisher_id}/packages

List all packages by publisher (all types)

GET /packages/{type}/{name}/{version}/dependencies

Return dependency tree for package (teams only)


6. Configuration (~/.agent-cli/config.json)
json{
  "verify_signatures": true,
  "trusted_publishers": [
    "jason@adcl",
    "security-team@company.com"
  ],
  "registry_url": "http://localhost:9090",
  "keyring_path": "~/.agent-cli/keyring",
  "strict_mode": true
}
Config options:

verify_signatures: Enable/disable signature verification
trusted_publishers: List of trusted publisher IDs
strict_mode: If true, fail on any untrusted dependency (even transitive)


7. Package Metadata Format (metadata.json)
Agent/MCP metadata:
json{
  "type": "agent",
  "name": "security-analyst",
  "version": "1.0.0",
  "publisher": "jason@adcl",
  "description": "Analyzes security scan results",
  "signature": {
    "algorithm": "GPG",
    "key_id": "ABC123DEF456",
    "fingerprint": "1234 5678 9ABC DEF0...",
    "created_at": "2025-10-17T12:00:00Z"
  },
  "checksums": {
    "sha256": "a1b2c3...",
    "md5": "x9y8z7..."
  },
  "published_at": "2025-10-17T12:00:00Z"
}
Team metadata (includes dependencies):
json{
  "type": "team",
  "name": "pentest",
  "version": "1.0.0",
  "publisher": "jason@adcl",
  "description": "Autonomous penetration testing team",
  "signature": {
    "algorithm": "GPG",
    "key_id": "ABC123DEF456",
    "fingerprint": "1234 5678 9ABC DEF0...",
    "created_at": "2025-10-17T12:00:00Z"
  },
  "dependencies": {
    "agents": [
      {"name": "security-analyst", "version": "1.0.0"},
      {"name": "reporter", "version": "1.2.0"}
    ],
    "mcps": [
      {"name": "nmap_recon", "version": "2.1.0"},
      {"name": "file_tools", "version": "1.0.0"}
    ]
  },
  "checksums": {
    "sha256": "a1b2c3...",
    "md5": "x9y8z7..."
  },
  "published_at": "2025-10-17T12:00:00Z"
}
```

---

## Test Cases

### Unit Tests
1. **GPG operations:**
   - Generate keypair → verify key in keyring
   - Sign file → verify .asc created and valid
   - Verify valid/invalid/missing signatures
   - Import/export keys round-trip

2. **Package types:**
   - Parse agent/mcp/team configs
   - Validate package structure
   - Extract dependencies from teams

3. **Dependency resolution:**
   - Build dependency tree from team
   - Detect circular dependencies
   - Handle missing dependencies

### Integration Tests
1. **Publisher workflow:**
   - keygen → sign agent → publish agent
   - keygen → sign mcp → publish mcp
   - sign team (with dependencies) → publish team

2. **User workflow:**
   - trust publisher → pull agent → verify
   - pull team → verify entire dependency tree
   - pull with untrusted dependency → fail appropriately

3. **Negative tests:**
   - Tampered package content → verification fails
   - Untrusted publisher → clear error
   - Missing dependency → fails with details
   - Invalid signature → specific error message
   - Team references non-existent agent → publish fails

4. **No-verify mode:**
   - Can install without verification
   - Warning displayed to user

---

## Error Messages

**Verification failures:**
```
❌ Signature verification failed for agent/security-analyst@1.0.0
   Publisher: jason@adcl
   Reason: Signature does not match file content
   
❌ Untrusted publisher: unknown@example.com
   Package: mcp/exploit-tools@2.0.0
   To trust: agent-cli trust unknown@example.com
   
❌ Dependency verification failed for team/pentest@1.0.0
   Failed packages:
   - agent/security-analyst@1.0.0: Invalid signature
   - mcp/nmap_recon@2.1.0: Publisher not trusted
   
⚠️  Installing without verification (--no-verify)
   This is not recommended for production use.
```

**Success messages:**
```
✓ Package team/pentest@1.0.0 verified successfully
  Verified dependencies:
  - agent/security-analyst@1.0.0 (jason@adcl)
  - agent/reporter@1.2.0 (jason@adcl)
  - mcp/nmap_recon@2.1.0 (jason@adcl)
  - mcp/file_tools@1.0.0 (jason@adcl)

Implementation Order

GPG wrapper module (isolated, testable)

Core signing/verification
Key management


Package type definitions (data models)

Agent, MCP, Team classes
Dependency structures


CLI keygen + sign commands (can test immediately)

Works for all three package types


Registry storage structure (filesystem layout)

Create directory structure
Metadata handling


Dependency verifier (core security logic)

Single package verification
Recursive tree verification


CLI trust + pull with verification (user workflow)

Trust management
Download + verify


Registry API endpoints (network layer)

Publish with verification
Download endpoints
Publisher key distribution


Integration tests (validate entire system)

Full workflows
Edge cases




Success Criteria

✅ Can generate keys and sign agents, MCPs, and teams
✅ Can publish all package types to registry
✅ Can trust publishers and pull verified packages
✅ Team installation verifies entire dependency tree
✅ Verification fails correctly for tampered/untrusted packages
✅ Clear error messages for all failure modes
✅ Works like yum install with gpgcheck=1
✅ Transitive dependency verification works
✅ Can operate in no-verify mode for development


Future Considerations (Not in MVP)

Key expiration and renewal
Key revocation lists
Multiple signatures per package
Signature timestamp validation
Offline verification mode
Publisher reputation system
