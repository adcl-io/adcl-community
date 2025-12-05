# Documentation Index

This directory contains detailed documentation for the MCP Agent Platform.

## Main Documentation (Root Directory)

- **[README.md](../README.md)** - Main project documentation, quick start, usage
- **[QUICK_START.md](../QUICK_START.md)** - Quick reference for common operations
- **[arch.md](../arch.md)** - Architecture and design decisions

## Setup & Configuration

- **[SCRIPTS.md](SCRIPTS.md)** - Management scripts reference
- **[SCRIPTS_FIXED.md](SCRIPTS_FIXED.md)** - Script improvements and fixes
- **[HOST_NETWORK_CONFIGURED.md](HOST_NETWORK_CONFIGURED.md)** - Host network setup for Nmap
- **[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)** - Using environment variables in workflows
- **[HOST_DOCKER_INTERNAL_FIX.md](HOST_DOCKER_INTERNAL_FIX.md)** - Container-to-host communication setup
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Project directory organization

## Integration Guides

- **[NMAP_INTEGRATION.md](NMAP_INTEGRATION.md)** - Nmap MCP server integration guide
- **[EXECUTION_VISUALIZATION.md](EXECUTION_VISUALIZATION.md)** - Real-time workflow visualization

## Automation & Triggers

- **[TRIGGER_PACKAGE_DEFINITION.md](TRIGGER_PACKAGE_DEFINITION.md)** - Trigger package specification and format
- **[TRIGGER_IMPLEMENTATION_PLAN.md](TRIGGER_IMPLEMENTATION_PLAN.md)** - Implementation roadmap and tasks

## Bug Fixes & Troubleshooting

### Parameter Substitution
- **[PARAMETER_SUBSTITUTION_FIXED.md](PARAMETER_SUBSTITUTION_FIXED.md)** - Template variable resolution fix
- **[FIX_SUMMARY.md](FIX_SUMMARY.md)** - User-facing fix summary

### UI/Rendering Issues
- **[BLANK_SCREEN_FIXED.md](BLANK_SCREEN_FIXED.md)** - React Error Boundary and service rendering fix
- **[BLANK_SCREEN_FINAL_DEBUG.md](BLANK_SCREEN_FINAL_DEBUG.md)** - Debugging guide
- **[BLANK_SCREEN_FIX.md](BLANK_SCREEN_FIX.md)** - Initial fix attempt
- **[AGENT_BLANK_SCREEN_DEBUG.md](AGENT_BLANK_SCREEN_DEBUG.md)** - Agent-specific debugging

### Docker & Deployment
- **[CONTAINERCONFIG_ERROR_FIXED.md](CONTAINERCONFIG_ERROR_FIXED.md)** - Docker restart error fix
- **[CONTAINERCONFIG_FIX_SUMMARY.txt](CONTAINERCONFIG_FIX_SUMMARY.txt)** - Quick reference
- **[CONTAINERCONFIG_ERROR.md](CONTAINERCONFIG_ERROR.md)** - Original issue documentation

### Performance & Timeouts
- **[TIMEOUT_FIX.md](TIMEOUT_FIX.md)** - Vulnerability scan timeout fix

## Comprehensive Summaries

- **[ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md)** - Complete summary of all fixes in session

## Test Files

All test files are located in the `../tests/` directory:
- `test_param_substitution.py` - Parameter resolution tests
- `test_nmap_workflow.py` - Nmap workflow tests
- `test_agent_response.py` - Agent response tests
- `check_results.py` - Results validation
- `test_frontend_rendering.html` - Frontend rendering tests

## Logs

Runtime logs are stored in the `../logs/` directory (configured via docker-compose volumes).

## Directory Structure

```
test3-dev-team/
├── README.md                   # Main documentation
├── QUICK_START.md             # Quick reference
├── arch.md                    # Architecture
├── docs/                      # Detailed documentation (this directory)
│   ├── INDEX.md              # This file
│   ├── *.md                  # Bug fixes, guides, troubleshooting
│   └── *.txt                 # Quick references
├── tests/                     # All test files
│   └── *.py, *.html          # Test scripts
├── logs/                      # Runtime logs (mounted from containers)
├── backend/                   # API server
├── frontend/                  # React UI
├── mcp_servers/              # MCP server implementations
└── workflows/                # Workflow definitions
```

## Document Categories

### 📚 Getting Started
- README.md (root)
- QUICK_START.md (root)
- arch.md (root)

### 🔧 Configuration
- SCRIPTS.md
- HOST_NETWORK_CONFIGURED.md
- ENVIRONMENT_VARIABLES.md
- HOST_DOCKER_INTERNAL_FIX.md
- PROJECT_STRUCTURE.md

### 🔌 Integration
- NMAP_INTEGRATION.md
- EXECUTION_VISUALIZATION.md

### 🔔 Automation & Triggers
- TRIGGER_PACKAGE_DEFINITION.md
- TRIGGER_IMPLEMENTATION_PLAN.md

### 🐛 Bug Fixes
- PARAMETER_SUBSTITUTION_FIXED.md
- BLANK_SCREEN_FIXED.md
- CONTAINERCONFIG_ERROR_FIXED.md
- TIMEOUT_FIX.md

### 📊 Summaries
- ALL_FIXES_SUMMARY.md
- FIX_SUMMARY.md
- CONTAINERCONFIG_FIX_SUMMARY.txt

### 🧪 Testing
- ../tests/ directory

---

**Tip:** Start with [README.md](../README.md) for an overview, then refer to specific guides as needed.
