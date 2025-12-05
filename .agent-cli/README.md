# Agent CLI Local Configuration

This directory contains local configuration for the agent CLI tool.

## Structure

```
.agent-cli/
├── config.json     # CLI configuration (registries, trusted publishers)
├── keyring/        # Imported publisher public keys (GPG home directory)
└── cache/          # Downloaded package cache
```

## config.json

Configuration file for agent CLI behavior:

```json
{
  "version": "1.0.0",
  "trusted_publishers": [
    "publisher_id_1",
    "publisher_id_2"
  ],
  "registries": [
    {
      "name": "local",
      "url": "file://./registry",
      "enabled": true,
      "priority": 1
    }
  ],
  "keyring_dir": "./.agent-cli/keyring",
  "cache_dir": "./.agent-cli/cache",
  "auto_verify": true,
  "allow_unsigned": false
}
```

### Fields

- **version**: Config file version
- **trusted_publishers**: List of trusted publisher IDs (fingerprints)
- **registries**: List of package registries to search
  - **name**: Registry identifier
  - **url**: Registry URL (file:// or http://)
  - **enabled**: Whether to search this registry
  - **priority**: Search order (lower = higher priority)
- **keyring_dir**: Path to GPG keyring with publisher keys
- **cache_dir**: Path to package cache
- **auto_verify**: Automatically verify signatures on download
- **allow_unsigned**: Allow installing unsigned packages (NOT RECOMMENDED)

## Keyring Directory

The `keyring/` directory is a GPG home directory containing imported publisher public keys.

**Adding a trusted publisher:**
```bash
# Import publisher's public key
gpg --homedir .agent-cli/keyring --import publisher.asc

# Add publisher ID to config.json trusted_publishers list
```

## Cache Directory

The `cache/` directory stores downloaded packages for faster access.

Cache structure:
```
cache/
└── {package_type}/
    └── {package_name}/
        └── {version}/
            ├── config.json
            ├── config.json.asc
            └── metadata.json
```

## Security Notes

⚠️ **IMPORTANT**:
- Never commit `.agent-cli/keyring/` to version control
- Review publisher keys before adding to trusted list
- Keep `allow_unsigned: false` in production
- Regularly update cached packages

## Usage

This directory is automatically created and managed by the agent CLI tool.

**Manual operations:**
```bash
# List imported keys
gpg --homedir .agent-cli/keyring --list-keys

# Clear cache
rm -rf .agent-cli/cache/*

# Reset configuration
cp .agent-cli/config.json .agent-cli/config.json.backup
# Edit config.json
```

## Production Deployment

In production, use `~/.agent-cli/` instead:

```bash
# Create production config directory
mkdir -p ~/.agent-cli/keyring ~/.agent-cli/cache

# Copy configuration
cp .agent-cli/config.json ~/.agent-cli/

# Update paths in config to use ~/.agent-cli/
```
