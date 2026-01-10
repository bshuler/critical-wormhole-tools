# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Security Model

Critical Wormhole Tools uses the Magic Wormhole protocol which provides:

- **End-to-end encryption** using NaCl (libsodium)
- **Password-Authenticated Key Exchange (PAKE)** for key derivation
- **Forward secrecy** through ephemeral Diffie-Hellman
- **No server-side key material** - relay servers cannot decrypt traffic

### Key Security Features

1. **Wormhole Codes**: Short, human-readable codes that encode cryptographic material
2. **WNS Identities**: Ed25519 keypairs for persistent addressing
3. **Transit Encryption**: All data is encrypted with authenticated encryption (ChaCha20-Poly1305 or AES-GCM)

### Threat Model

We protect against:
- Passive network observers
- Malicious relay servers (limited to denial of service)
- MITM attacks (wormhole code verification)

We do NOT protect against:
- Compromised endpoints
- Code guessing (use strong, long codes for sensitive transfers)
- Side-channel attacks on local system

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of these methods:

1. **GitHub Security Advisories**: Use the "Report a vulnerability" button in the Security tab
2. **Email**: security@example.com (encrypted reports welcome, PGP key available on request)

### What to Include

When reporting a vulnerability, please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Resolution Target**: Within 90 days for critical issues

### Disclosure Policy

We follow coordinated disclosure:

1. We will acknowledge receipt of your report
2. We will investigate and determine the impact
3. We will develop and test a fix
4. We will release the fix and credit you (unless you prefer anonymity)
5. After the fix is released, we may publish a security advisory

## Security Best Practices

### For Users

1. **Verify wormhole codes** out-of-band when possible
2. **Use strong codes** for sensitive transfers (add extra words)
3. **Keep software updated** to receive security fixes
4. **Protect your WNS identity keys** stored in `~/.wh/identity/`
5. **Use `--verify` mode** when available for additional code verification

### For Developers

1. **Never commit secrets** (use environment variables)
2. **Pin dependencies** to known-good versions
3. **Run security checks**: `pip-audit`, `safety check`
4. **Follow secure coding practices** for any contributions

## Dependencies

Our security depends on these well-audited libraries:

- **magic-wormhole**: Core protocol implementation
- **PyNaCl**: Python bindings for libsodium
- **AsyncSSH**: SSH protocol implementation
- **cryptography**: Cryptographic primitives

We monitor dependencies for vulnerabilities using:
- Dependabot (GitHub)
- pip-audit
- Safety

## Acknowledgments

We thank the following for their security contributions:

- (Your name could be here!)

---

This security policy is subject to change. Check back regularly for updates.
