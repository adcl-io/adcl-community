# ADCL Platform - Community Edition

AI-Driven Cyber Lab (ADCL) Platform - Open source AI agent orchestration system.

## Quick Start

Install ADCL in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash
```

This will:
1. Download configuration files
2. Pull Docker images from GHCR
3. Start the platform

Access the UI at: http://localhost:3000

## Manual Installation

```bash
# Clone the repository
git clone https://github.com/adcl-io/adcl-community.git
cd adcl-community

# Create .env file
cp .env.example .env
# Edit .env and add your API keys

# Start the platform
docker compose up -d
```

## Configuration

Edit `.env` to configure:
- API keys (Anthropic, OpenAI)
- Port numbers
- Other settings

## Images

Docker images are hosted on GitHub Container Registry (GHCR):
- `ghcr.io/adcl-io/adcl-community/orchestrator:latest`
- `ghcr.io/adcl-io/adcl-community/frontend:latest`
- `ghcr.io/adcl-io/adcl-community/registry:latest`

## Version

Current version: **0.1.12**

## License

See LICENSE file for details.

## Documentation

For full documentation, visit: https://docs.adcl.io

## Support

- Issues: https://github.com/adcl-io/adcl-community/issues
- Discussions: https://github.com/adcl-io/adcl-community/discussions

## Enterprise Edition

For enterprise features, support, and SLA, contact: enterprise@adcl.io
