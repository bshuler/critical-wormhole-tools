# Privacy Policy for Wormhole Browser Extension

**Last Updated**: 2026-01-23

## Overview

The Wormhole Browser Extension ("Extension") is developed by the Critical Wormhole Team. This privacy policy explains what data the Extension collects, how it's used, and your rights regarding your data.

## Summary

- **We do not collect personal data**
- **We do not use analytics or tracking**
- **All data stays on your device**
- **All connections are end-to-end encrypted**

## Data Collection

### Data We Collect

The Extension stores the following data **locally on your device only**:

| Data Type | Purpose | Storage Location |
|-----------|---------|------------------|
| Recent wormhole codes | Quick access to recent connections | Browser local storage |
| Connection preferences | Remember your proxy settings | Browser local storage |
| WNS identity keys | Your cryptographic identity for WNS | Browser local storage |
| Trusted hosts | TOFU trust decisions for WNS addresses | Browser local storage |

### Data We Do NOT Collect

- Personal information (name, email, etc.)
- Browsing history
- Website content accessed through wormhole
- Analytics or telemetry
- Crash reports
- Usage statistics

## Data Transmission

### Wormhole Relay Servers

When you connect to a wormhole address, the Extension communicates with wormhole relay servers. This communication:

- Uses the Magic Wormhole protocol
- Is **end-to-end encrypted** (relay servers cannot read your data)
- Only transmits an encrypted session key negotiation
- Does not transmit any personal information

### Local Daemon

The Extension communicates with a local daemon (`wh daemon`) running on your computer via HTTP on `localhost:9475`. This communication:

- Never leaves your computer
- Is used to establish wormhole connections
- Is used to resolve WNS addresses

## Permissions Explained

The Extension requests these browser permissions:

| Permission | Why It's Needed |
|------------|-----------------|
| `proxy` | Configure browser to route `wh://` URLs through the wormhole proxy |
| `storage` | Save your preferences and recent connections locally |
| `scripting` | Intercept and handle `wh://` URL navigation |
| `tabs` | Redirect tabs to wormhole viewer for `wh://` URLs |
| `<all_urls>` | Required for the proxy configuration to work with any website |

## Third-Party Services

The Extension does not use any third-party services for:
- Analytics
- Advertising
- Error reporting
- User tracking

The only external communication is with wormhole relay servers, which is essential for the Extension to function.

## Data Security

- All wormhole connections use **SPAKE2 key exchange** (Password Authenticated Key Exchange)
- Data in transit is encrypted with **NaCl secretbox** (XSalsa20-Poly1305)
- WNS identities use **Ed25519** cryptographic keys
- No data is transmitted to our servers or any third party

## Data Retention

All data is stored locally on your device. To delete it:

1. **Clear Extension Data**: Right-click the extension icon → Manage Extensions → Clear Site Data
2. **Uninstall Extension**: This removes all stored data

## Children's Privacy

The Extension does not knowingly collect data from children under 13. The Extension is designed for general use and does not target children.

## Changes to This Policy

If we update this privacy policy, we will:
1. Update the "Last Updated" date
2. Notify users through the Extension changelog

## Contact

For privacy questions or concerns:
- **GitHub Issues**: https://github.com/bshuler/critical-wormhole-tools/issues
- **Email**: privacy@critical-wormhole.tools (if available)

## Your Rights

Depending on your jurisdiction, you may have rights to:
- Access your data (it's all stored locally - you already have access)
- Delete your data (clear browser storage or uninstall)
- Data portability (export from browser local storage)

Since all data is stored locally on your device, you have complete control over your data at all times.
