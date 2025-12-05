# GPG Passphrase Configuration Guide

## Overview

The GPG package signing system supports reading signing key passphrases from environment variables, enabling automated package signing workflows while maintaining security.

---

## Configuration

### 1. Environment Variable Setup

Add your GPG signing passphrase to the `.env` file:

```bash
# .env
GPG_SIGNING_PASSPHRASE=your_secure_passphrase_here
```

**Important Security Notes:**
- ⚠️ **Never commit `.env` to version control** (it's in .gitignore)
- ✅ Use strong, unique passphrases (20+ characters recommended)
- ✅ Restrict file permissions: `chmod 600 .env`
- ✅ In production, use secret management systems (HashiCorp Vault, AWS Secrets Manager, etc.)

---

## Usage

### Generating Keys with Passphrase

```python
from src.signing import gpg
from src.utils import load_env_file

# Load environment variables from .env
load_env_file()

# Generate keypair (automatically uses GPG_SIGNING_PASSPHRASE from env)
key_id = gpg.generate_keypair(
    email="publisher@example.com",
    name="Publisher Name"
)

# Or explicitly provide passphrase
key_id = gpg.generate_keypair(
    email="publisher@example.com",
    name="Publisher Name",
    passphrase="explicit_passphrase"
)
```

### Signing Files with Passphrase

```python
from src.signing import gpg
from src.utils import load_env_file

# Load .env file
load_env_file()

# Sign file (automatically uses GPG_SIGNING_PASSPHRASE from env)
signature_path = gpg.sign_file(
    filepath="/path/to/package.json",
    key_id="YOUR_KEY_ID"
)

# Or explicitly provide passphrase
signature_path = gpg.sign_file(
    filepath="/path/to/package.json",
    key_id="YOUR_KEY_ID",
    passphrase="explicit_passphrase"
)
```

---

## Passphrase Priority

The system checks for passphrases in this order:

1. **Explicit parameter** - If `passphrase` is provided to the function
2. **Environment variable** - `GPG_SIGNING_PASSPHRASE` from `.env` or system environment
3. **Empty passphrase** - Falls back to no passphrase (not recommended for production)

```python
# Priority demonstration
from src.signing import gpg

# 1. Explicit passphrase (highest priority)
key_id = gpg.generate_keypair(
    email="test@example.com",
    name="Test",
    passphrase="explicit_pass"  # This is used
)

# 2. Environment variable (if no explicit passphrase)
import os
os.environ['GPG_SIGNING_PASSPHRASE'] = 'env_pass'
key_id = gpg.generate_keypair(
    email="test@example.com",
    name="Test"
    # Uses 'env_pass' from environment
)

# 3. Empty passphrase (if neither above is set)
os.environ.pop('GPG_SIGNING_PASSPHRASE', None)
key_id = gpg.generate_keypair(
    email="test@example.com",
    name="Test"
    # Uses empty passphrase (key is not protected)
)
```

---

## Best Practices

### Development Environment

```bash
# .env (local development)
GPG_SIGNING_PASSPHRASE=dev_passphrase_1234
```

### CI/CD Pipeline

**GitHub Actions:**
```yaml
# .github/workflows/sign-packages.yml
- name: Sign packages
  env:
    GPG_SIGNING_PASSPHRASE: ${{ secrets.GPG_SIGNING_PASSPHRASE }}
  run: |
    python sign_packages.py
```

**GitLab CI:**
```yaml
# .gitlab-ci.yml
sign_packages:
  script:
    - python sign_packages.py
  variables:
    GPG_SIGNING_PASSPHRASE: $GPG_SIGNING_PASSPHRASE
```

### Production Deployment

**Docker:**
```dockerfile
# Pass as build arg or runtime env
docker run -e GPG_SIGNING_PASSPHRASE="${GPG_SIGNING_PASSPHRASE}" my-app
```

**Kubernetes Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gpg-signing-secret
type: Opaque
data:
  passphrase: base64_encoded_passphrase
---
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: signer
    env:
    - name: GPG_SIGNING_PASSPHRASE
      valueFrom:
        secretKeyRef:
          name: gpg-signing-secret
          key: passphrase
```

---

## Security Considerations

### ✅ DO

- **Use strong passphrases**: 20+ characters with mixed case, numbers, symbols
- **Rotate passphrases regularly**: Every 90 days recommended
- **Use secret management**: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
- **Restrict file permissions**: `chmod 600 .env`
- **Use separate keys**: Different keys for dev, staging, production
- **Monitor key usage**: Log all signing operations
- **Backup keys securely**: Encrypted backups with separate passphrase

### ❌ DON'T

- **Don't commit passphrases** to version control
- **Don't share passphrases** via email, Slack, etc.
- **Don't use weak passphrases** like "password123"
- **Don't reuse passphrases** across different keys
- **Don't store passphrases** in plain text files outside of .env
- **Don't log passphrases** in application logs

---

## Troubleshooting

### Wrong Passphrase Error

```python
ValueError: Failed to sign file: bad passphrase. Check GPG_SIGNING_PASSPHRASE environment variable.
```

**Solutions:**
1. Verify `.env` file contains correct passphrase
2. Ensure `.env` file is in the correct directory
3. Check passphrase has no extra spaces or quotes
4. Reload environment: `from src.utils import load_env_file; load_env_file()`

### Passphrase Not Loading

```python
# Debug: Check if passphrase is set
import os
print(os.getenv('GPG_SIGNING_PASSPHRASE'))  # Should print your passphrase

# If None, load .env explicitly
from src.utils import load_env_file
load_env_file()
print(os.getenv('GPG_SIGNING_PASSPHRASE'))  # Should now print passphrase
```

### Key Without Passphrase

If you generated a key without a passphrase and want to add one:

```bash
# Interactive passphrase change
gpg --edit-key YOUR_KEY_ID
gpg> passwd
# Enter new passphrase
gpg> save
```

---

## Example Workflow

### Complete Signing Workflow

```python
#!/usr/bin/env python3
"""
Example: Sign a package with passphrase from .env
"""

from pathlib import Path
from src.signing import gpg
from src.registry.package_types import Package, PackageType
from src.utils import load_env_file
import json

# 1. Load environment variables
load_env_file()

# 2. Create or load your package
config = {
    'name': 'my-agent',
    'version': '1.0.0',
    'publisher': 'me@example.com',
    'description': 'My awesome agent'
}

package = Package.from_config(config, PackageType.AGENT)

# 3. Write package config
package_dir = Path('./packages/my-agent/1.0.0')
package_dir.mkdir(parents=True, exist_ok=True)

config_file = package_dir / 'agent.json'
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

# 4. Sign the package (uses GPG_SIGNING_PASSPHRASE from .env)
signature_path = gpg.sign_file(
    filepath=str(config_file),
    key_id='YOUR_KEY_ID'  # Replace with your actual key ID
)

print(f"✅ Package signed successfully!")
print(f"   Config: {config_file}")
print(f"   Signature: {signature_path}")

# 5. Verify the signature
is_valid, error = gpg.verify_signature(
    filepath=str(config_file),
    signature_path=signature_path
)

if is_valid:
    print(f"✅ Signature verified!")
else:
    print(f"❌ Verification failed: {error}")
```

---

## Testing

### Unit Tests with Passphrases

```python
import pytest
from src.signing import gpg
from src.utils import set_gpg_passphrase

def test_sign_with_passphrase(temp_keyring, test_file):
    """Test signing with passphrase from environment"""

    # Set test passphrase
    test_passphrase = "test_passphrase_123"
    set_gpg_passphrase(test_passphrase)

    # Generate key (uses passphrase from env)
    key_id = gpg.generate_keypair(
        email="test@example.com",
        name="Test User",
        keyring_dir=temp_keyring
    )

    # Sign file (uses same passphrase from env)
    signature_path = gpg.sign_file(
        filepath=test_file,
        key_id=key_id,
        keyring_dir=temp_keyring
    )

    assert Path(signature_path).exists()
```

---

## Migration Guide

### From Unprotected Keys to Protected Keys

If you have existing keys without passphrases:

```bash
# 1. Add passphrase to existing key
gpg --edit-key YOUR_KEY_ID
gpg> passwd
# Enter new passphrase twice
gpg> save

# 2. Add passphrase to .env
echo "GPG_SIGNING_PASSPHRASE=your_new_passphrase" >> .env

# 3. Test signing
python -c "
from src.signing import gpg
from src.utils import load_env_file
load_env_file()
gpg.sign_file('test.json', 'YOUR_KEY_ID')
print('✅ Signing works with passphrase!')
"
```

---

## Additional Resources

- [GPG Manual](https://www.gnupg.org/documentation/manuals/gnupg/)
- [Python-GnuPG Documentation](https://gnupg.readthedocs.io/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

---

**Last Updated**: 2025-10-17
**Version**: 1.0.0
