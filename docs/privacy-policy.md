# Critical Wormhole Tools - Privacy Policy

**Last Updated**: 2026-01-23

This privacy policy covers all Critical Wormhole Tools software, including the CLI tools, browser extension, and discovery site.

---

## Our Commitment

Critical Wormhole Tools is designed with privacy as a core principle:

- **Zero data collection** - We don't collect any user data
- **No accounts required** - Use the tools without registration
- **End-to-end encryption** - All data is encrypted before transmission
- **Local-first** - Your data stays on your device

---

## Browser Extension

See the complete [Browser Extension Privacy Policy](../browser-extension/PRIVACY.md) for details.

**Summary:**
- No personal data collected
- No analytics or tracking
- All preferences stored locally
- All connections end-to-end encrypted

---

## CLI Tools (`wh` commands)

### Data Collection

The CLI tools do **not** collect any data. All operations are:
- Peer-to-peer (no central servers except relay)
- End-to-end encrypted
- Performed locally on your device

### Wormhole Relay Communication

When you use wormhole tools, your device communicates with relay servers to establish connections. The relay servers:

- **Cannot read your data** (end-to-end encrypted)
- **Do not log connections** (unless you run your own relay with logging enabled)
- **Only see encrypted handshake data**

### Configuration Files

The CLI stores configuration locally in `~/.wh/`:

| File/Directory | Contents |
|----------------|----------|
| `~/.wh/identity/` | Your WNS cryptographic keys |
| `~/.wh/aliases.json` | Local alias mappings |
| `~/.wh/known_hosts/` | TOFU trusted public keys |
| `~/.wh/config.json` | User preferences |

All files are stored locally and never transmitted.

---

## Discovery Site

The standalone discovery site (hosted on GitHub Pages) follows the same principles:

- **No server-side code** - Pure static JavaScript
- **No analytics** - No tracking scripts
- **Local storage only** - Preferences stored in your browser
- **E2E encryption** - All wormhole connections encrypted

---

## Wormhole Name Service (WNS)

WNS uses a distributed hash table (DHT) for name resolution:

- Your public key is published to the DHT (this is public by design)
- Private keys never leave your device
- The DHT uses the public BitTorrent Mainline DHT
- Advertisements are cryptographically signed

---

## Self-Hosted Relay

If you run your own relay server (`wh relay`):

- You control all logging settings
- By default, minimal operational logs only
- No user data is logged unless you configure it
- Relay cannot decrypt user traffic (E2E encryption)

---

## Security

For security-related information, see [SECURITY.md](../SECURITY.md).

---

## Contact

For privacy questions:
- **GitHub Issues**: https://github.com/bshuler/critical-wormhole-tools/issues

---

## Changes

This policy may be updated. Changes will be reflected in the "Last Updated" date and documented in the CHANGELOG.
