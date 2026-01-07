# Wormhole Protocol Specification

**Version**: 1.0
**Status**: Draft
**Authors**: Critical Wormhole Team

---

## Abstract

This document specifies the Wormhole Protocol, a system for establishing secure, authenticated connections between two parties using short, human-readable codes. It extends the Magic Wormhole protocol with a persistent addressing layer called the Wormhole Name Service (WNS).

The protocol enables:
- Secure key exchange using SPAKE2 (Password-Authenticated Key Exchange)
- NAT traversal via relay servers
- Persistent, self-certifying addresses derived from public keys
- Distributed name resolution via DHT

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Protocol](#2-core-protocol)
3. [Wormhole Name Service (WNS)](#3-wormhole-name-service-wns)
4. [Discovery and Resolution](#4-discovery-and-resolution)
5. [Naming Hierarchy](#5-naming-hierarchy)
6. [Wire Formats](#6-wire-formats)
7. [Security Considerations](#7-security-considerations)
8. [Implementation Notes](#8-implementation-notes)

---

## 1. Introduction

### 1.1 Problem Statement

Traditional network connections require IP addresses or DNS names, which:
- Require static IPs or DNS configuration
- Don't work behind NAT without port forwarding
- Expose network topology information
- Require trust in DNS infrastructure

The Wormhole Protocol solves these problems by:
- Using short, memorable codes for connection establishment
- Providing automatic NAT traversal
- Encrypting all traffic end-to-end
- Eliminating reliance on DNS for addressing

### 1.2 Design Goals

1. **Human-friendly**: Codes should be easy to communicate verbally
2. **Secure**: No trust required in relay infrastructure
3. **NAT-friendly**: Work across firewalls and NAT
4. **Decentralized**: No single point of failure for name resolution
5. **Self-certifying**: Addresses cryptographically bound to identity

### 1.3 Terminology

| Term | Definition |
|------|------------|
| **Wormhole** | A secure, authenticated channel between two parties |
| **Code** | A short, human-readable string used for initial pairing |
| **Nameplate** | A short numeric identifier for the mailbox |
| **Mailbox** | A server-side rendezvous point for message exchange |
| **Transit** | Direct peer-to-peer or relayed data connection |
| **WNS Address** | A persistent, self-certifying address |
| **Advertisement** | A signed message announcing current wormhole code |

---

## 2. Core Protocol

### 2.1 Overview

The Wormhole Protocol operates in three phases:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Connection Establishment                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Rendezvous          Phase 2: Key Exchange             │
│  ┌─────────┐                  ┌─────────┐                       │
│  │ Client  │◄── Mailbox ────►│ Server  │                       │
│  └─────────┘    Server        └─────────┘                       │
│       │                            │                            │
│       │         SPAKE2             │                            │
│       │◄─────────────────────────►│                            │
│       │                            │                            │
│  Phase 3: Transit                                               │
│       │                            │                            │
│       │◄═══ Encrypted Channel ═══►│                            │
│       │    (Direct or Relayed)     │                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Wormhole Code Format

A wormhole code consists of:
```
<nameplate>-<word1>-<word2>[-<word3>...]

Examples:
  7-guitar-sunset
  42-castle-thunder-river
  1-alpha-beta
```

**Components**:
- **Nameplate**: Numeric identifier (1-999), allocated by mailbox server
- **Words**: Random words from a wordlist, providing entropy

**Entropy Calculation**:
- 2 words from 256-word list: 16 bits
- 3 words from 256-word list: 24 bits
- Recommended: 2 words for interactive use, 3+ for automated

### 2.3 SPAKE2 Key Exchange

The protocol uses SPAKE2 (Simple Password-Authenticated Key Exchange) to derive a shared secret from the wormhole code.

**SPAKE2 Parameters**:
```
Group:        Ed25519 curve
Password:     UTF-8 encoded wormhole code
Identity A:   "side-" + hex(random_bytes(5))
Identity B:   "side-" + hex(random_bytes(5))
M:            Fixed curve point (see RFC 9383)
N:            Fixed curve point (see RFC 9383)
```

**Protocol Flow**:
```
Alice (side-a)                          Bob (side-b)
─────────────────                       ─────────────
x = random_scalar()                     y = random_scalar()
X = x*G + pw*M                          Y = y*G + pw*N
        ─────── send X ──────►
        ◄────── send Y ───────
K_a = x*(Y - pw*N)                      K_b = y*(X - pw*M)

        K_a == K_b (shared secret)
```

**Key Derivation**:
```
master_key = HKDF-SHA256(
    salt = "wormhole:master_key",
    ikm = K,
    info = sorted(side_a, side_b)
)

session_key = HKDF-SHA256(
    salt = "wormhole:session_key",
    ikm = master_key,
    info = "session"
)
```

### 2.4 Mailbox Protocol

The mailbox server provides rendezvous via WebSocket.

**Server URL**: `wss://relay.example.com/v1`

**Message Format** (JSON):
```json
{
  "type": "<message_type>",
  "id": "<request_id>",
  ...message_specific_fields
}
```

**Message Types**:

| Type | Direction | Description |
|------|-----------|-------------|
| `bind` | C→S | Associate with app_id |
| `allocate` | C→S | Request new nameplate |
| `allocated` | S→C | Nameplate assigned |
| `claim` | C→S | Claim existing nameplate |
| `claimed` | S→C | Nameplate claimed |
| `open` | C→S | Open mailbox |
| `add` | C→S | Add message to mailbox |
| `message` | S→C | Message received |
| `release` | C→S | Release nameplate |
| `close` | C→S | Close mailbox |

**Typical Flow**:
```
Client A                    Server                    Client B
────────                    ──────                    ────────
bind(app_id) ────────────►
◄──────────────── ack
allocate ─────────────────►
◄──────────── allocated(7)
claim(7) ──────────────────────────────────────────► claim(7)
open(mailbox_7) ─────────►              ◄──────────── open(mailbox_7)
add(phase="pake", body=X) ─────────────────────────►
◄─────────────────────────────────────── add(phase="pake", body=Y)
                    ... key exchange completes ...
release ──────────────────►              ◄──────────── release
close ────────────────────►              ◄──────────── close
```

### 2.5 Transit Protocol

After key exchange, parties establish a direct connection for data transfer.

**Connection Methods** (in preference order):
1. Direct TCP connection (if both have public IPs)
2. Direct TCP via UPnP port mapping
3. TCP hole-punching
4. Relay server

**Transit Hints** (exchanged via mailbox):
```json
{
  "type": "relay-v1",
  "hints": [
    {"type": "direct-tcp-v1", "hostname": "192.168.1.5", "port": 4001},
    {"type": "relay-v1", "hints": [
      {"type": "tcp", "hostname": "relay.example.com", "port": 4001}
    ]}
  ]
}
```

**Handshake** (over transit connection):
```
Initiator sends:    "transit sender " + hex(transit_key) + " ready\n\n"
Responder sends:    "transit receiver " + hex(transit_key) + " ready\n\n"
                    "go\n"
```

**Encryption** (after handshake):
- Algorithm: XSalsa20-Poly1305 (NaCl secretbox)
- Key: `transit_key = HKDF(master_key, "transit_key")`
- Nonce: Incrementing counter (8 bytes), prefixed to each message

### 2.6 Dilation (Persistent Connections)

Dilation extends a wormhole into a persistent, multiplexed channel.

**Subchannel Structure**:
```
┌─────────────────────────────────────────┐
│            Dilated Wormhole             │
├─────────────────────────────────────────┤
│  Subchannel 0: Control                  │
│  Subchannel 1: User data                │
│  Subchannel 2: User data                │
│  ...                                    │
└─────────────────────────────────────────┘
```

**Frame Format**:
```
┌──────────┬──────────┬─────────────────┐
│ Type (1) │ Subchan  │ Payload         │
│          │ (4)      │ (variable)      │
└──────────┴──────────┴─────────────────┘
```

**Frame Types**:
| Type | Name | Description |
|------|------|-------------|
| 0x01 | OPEN | Open new subchannel |
| 0x02 | DATA | Data on subchannel |
| 0x03 | CLOSE | Close subchannel |
| 0x04 | ACK | Flow control acknowledgment |

---

## 3. Wormhole Name Service (WNS)

### 3.1 Overview

WNS provides persistent, self-certifying addresses that map to ephemeral wormhole codes. This enables:
- Bookmarkable wormhole addresses
- Persistent services accessible via stable identifiers
- Trust establishment via public key fingerprints

### 3.2 Identity Generation

An identity consists of an Ed25519 keypair:

```
private_key = random_bytes(32)
public_key = ed25519_derive_public(private_key)
```

### 3.3 Address Derivation

The WNS address is derived from the public key:

```
address = base32_encode(sha256(public_key)[0:16]).lower()

# Result: 26 character string
# Example: "a7b3c9d2e1f4g5h6i7j8k9l0m1"
```

**Properties**:
- 128 bits of collision resistance
- Self-certifying: address is bound to public key
- Case-insensitive for human communication

### 3.4 Full Address Format

```
wh://<address>.wns
wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns

# With optional components:
wh://[user@]<address>.wns[:port][/path]
wh://admin@a7b3c9d2e1f4g5h6.wns:22/home
```

### 3.5 Code Advertisement

A server announces its current wormhole code via signed advertisements:

```json
{
  "version": 1,
  "address": "a7b3c9d2e1f4g5h6i7j8k9l0m1",
  "public_key": "<base64-encoded-ed25519-public-key>",
  "code": "7-guitar-sunset",
  "timestamp": "2024-01-15T10:30:00Z",
  "expires": "2024-01-15T10:35:00Z",
  "scoped_name": "laptop",
  "services": ["ssh", "http"],
  "signature": "<base64-encoded-ed25519-signature>"
}
```

**Signature Computation**:
```
canonical = json_canonicalize(advertisement_without_signature)
signature = ed25519_sign(private_key, canonical)
```

### 3.6 Advertisement Verification

Clients verify advertisements:

```python
def verify_advertisement(ad):
    # 1. Check address matches public key
    expected_address = derive_address(ad.public_key)
    assert ad.address == expected_address

    # 2. Check not expired
    assert datetime.now() < ad.expires

    # 3. Verify signature
    canonical = json_canonicalize(ad.without_signature())
    assert ed25519_verify(ad.public_key, canonical, ad.signature)

    return True
```

### 3.7 Trust Model (TOFU)

WNS uses Trust-On-First-Use:

1. First connection: Client stores server's public key
2. Subsequent connections: Client verifies public key matches stored value
3. Key change: Client warned of potential MITM attack

**Known Hosts Storage**:
```json
{
  "address": "a7b3c9d2e1f4g5h6i7j8k9l0m1",
  "public_key": "<base64>",
  "first_seen": "2024-01-15T10:30:00Z",
  "last_seen": "2024-01-20T15:45:00Z",
  "display_name": "My Server"
}
```

---

## 4. Discovery and Resolution

### 4.1 Discovery Methods

WNS supports multiple discovery mechanisms:

| Method | Decentralized | Offline | Priority |
|--------|---------------|---------|----------|
| DHT | Yes | No | 1 (Primary) |
| HTTP Well-Known | No | No | 2 |
| Local Cache | Yes | Yes | 3 |
| Manual | Yes | Yes | 4 |

### 4.2 DHT Discovery

Primary discovery uses a Kademlia DHT:

**DHT Parameters**:
```
Node ID:        sha256(public_key)
Key:            sha256("wns:" + address)
Value:          JSON advertisement (signed)
TTL:            5 minutes (republish every 4 minutes)
Replication:    k=20
```

**Bootstrap Nodes**:
```
wns-bootstrap-1.example.com:8468
wns-bootstrap-2.example.com:8468
wns-bootstrap-3.example.com:8468
```

**Lookup Flow**:
```
1. Client computes: key = sha256("wns:" + address)
2. Client queries DHT for key
3. DHT returns signed advertisement
4. Client verifies signature
5. Client connects using code from advertisement
```

### 4.3 HTTP Well-Known Discovery

Fallback for servers with web presence:

```
GET https://<domain>/.well-known/wormhole/<address>.json
```

**Response**:
```json
{
  "version": 1,
  "address": "a7b3c9d2e1f4g5h6i7j8k9l0m1",
  "advertisement": { ... signed advertisement ... }
}
```

### 4.4 Local Resolution

For offline/air-gapped scenarios:

**QR Code**: Advertisement encoded as QR code
**File**: Advertisement saved to `.wns` file
**Manual**: User enters code directly

### 4.5 Resolution Algorithm

```python
async def resolve(address):
    # 1. Check local cache
    cached = cache.get(address)
    if cached and not cached.expired:
        return cached

    # 2. Try DHT (with timeout)
    try:
        ad = await dht.lookup(address, timeout=5.0)
        if verify_advertisement(ad):
            cache.put(address, ad)
            return ad
    except TimeoutError:
        pass

    # 3. Try HTTP well-known (if domain configured)
    domain = get_domain_hint(address)
    if domain:
        ad = await http_lookup(domain, address)
        if verify_advertisement(ad):
            cache.put(address, ad)
            return ad

    # 4. Use stale cache if available
    if cached:
        return cached  # May fail, but worth trying

    raise ResolutionError(f"Cannot resolve {address}")
```

---

## 5. Naming Hierarchy

### 5.1 Address Types

WNS supports a hierarchy of naming schemes:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Naming Hierarchy                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Most Specific                              Least Specific       │
│  ◄──────────────────────────────────────────────────────────►   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Ephemeral│  │  WNS     │  │ Scoped   │  │ Global / Alias   │ │
│  │ Code     │  │ Address  │  │ Name     │  │                  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│                                                                  │
│  7-guitar-   wh://a7b3...   wh://laptop.  wh://my-server.wns   │
│  sunset      wns            a7b3...wns    server (alias)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Ephemeral Codes

Traditional wormhole codes for one-time connections:

```
Format:     <nameplate>-<words>
Example:    7-guitar-sunset
Lifetime:   Single use (consumed on connection)
Trust:      Code itself provides authentication
```

### 5.3 WNS Addresses (Self-Certifying)

Persistent addresses derived from public key:

```
Format:     wh://<address>.wns
Example:    wh://a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
Lifetime:   Permanent (as long as private key is retained)
Trust:      Public key verification + TOFU
```

### 5.4 Scoped Names

Human-readable names controlled by address owner:

```
Format:     wh://<name>.<address>.wns
Example:    wh://laptop.a7b3c9d2e1f4g5h6i7j8k9l0m1.wns
Lifetime:   Set by owner, included in advertisement
Trust:      Same as WNS address
```

**Scoped Name Rules**:
- 1-63 characters
- Lowercase alphanumeric + hyphen
- Cannot start/end with hyphen
- Owner can change at any time

### 5.5 Global Names

First-come-first-served names registered in DHT:

```
Format:     wh://<name>.wns
Example:    wh://my-server.wns
Lifetime:   7 days (must be renewed)
Trust:      DHT registration + signature verification
```

**Global Name Claim**:
```json
{
  "version": 1,
  "name": "my-server",
  "address": "a7b3c9d2e1f4g5h6i7j8k9l0m1",
  "public_key": "<base64>",
  "claimed_at": "2024-01-15T10:30:00Z",
  "expires": "2024-01-22T10:30:00Z",
  "signature": "<base64>"
}
```

**Registration Rules**:
- 3-63 characters
- Lowercase alphanumeric + hyphen
- First valid claim wins
- Must renew before expiry
- Cannot transfer (must release and re-claim)

### 5.6 Local Aliases (Petnames)

User-defined local shortcuts:

```
Format:     <alias>
Example:    server, laptop, work-machine
Storage:    Local to client
Trust:      User-managed mapping
```

**Alias Storage**:
```json
{
  "aliases": {
    "server": {
      "address": "wh://a7b3c9d2e1f4g5h6.wns",
      "username": "admin",
      "created": "2024-01-15T10:30:00Z"
    },
    "laptop": {
      "address": "wh://x9y8z7w6v5u4.wns",
      "created": "2024-01-16T14:20:00Z"
    }
  }
}
```

### 5.7 Resolution Priority

When resolving a name:

```python
def resolve_name(name):
    # 1. Check if it's an ephemeral code
    if is_ephemeral_code(name):  # matches N-word-word pattern
        return EphemeralCode(name)

    # 2. Check if it's a full WNS address
    if name.startswith("wh://"):
        return parse_wns_address(name)

    # 3. Check local aliases
    alias = aliases.get(name)
    if alias:
        return parse_wns_address(alias.address)

    # 4. Check if it's a global name
    if is_valid_global_name(name):
        return resolve_global_name(name)

    raise UnknownNameError(name)
```

---

## 6. Wire Formats

### 6.1 JSON Canonicalization

For signature computation, JSON must be canonicalized:

```
1. No whitespace between tokens
2. Object keys sorted lexicographically
3. No trailing commas
4. Unicode escape sequences in lowercase
5. Numbers without unnecessary precision
```

**Example**:
```json
{"address":"a7b3c9d2","code":"7-guitar","timestamp":"2024-01-15T10:30:00Z"}
```

### 6.2 Base64 Encoding

All binary data uses standard Base64 (RFC 4648):
- Alphabet: A-Z, a-z, 0-9, +, /
- Padding: Required (=)

### 6.3 Base32 Encoding (Addresses)

Addresses use lowercase Base32 without padding:
- Alphabet: a-z, 2-7
- No padding

### 6.4 Timestamp Format

All timestamps use ISO 8601 with UTC timezone:
```
YYYY-MM-DDTHH:MM:SSZ
2024-01-15T10:30:00Z
```

### 6.5 DHT Message Format

DHT messages use MessagePack encoding:

```
STORE:
{
  "type": "store",
  "key": <32 bytes>,
  "value": <JSON advertisement as UTF-8 bytes>,
  "ttl": <integer seconds>
}

FIND_VALUE:
{
  "type": "find_value",
  "key": <32 bytes>
}

FIND_VALUE_RESPONSE:
{
  "type": "find_value_response",
  "found": true,
  "value": <JSON advertisement as UTF-8 bytes>
}
```

---

## 7. Security Considerations

### 7.1 Threat Model

**Trusted**:
- Client and server endpoints
- Cryptographic primitives (Ed25519, SPAKE2, XSalsa20-Poly1305)

**Untrusted**:
- Network (all traffic assumed observable)
- Mailbox relay server
- Transit relay server
- DHT nodes

### 7.2 SPAKE2 Security

- Provides mutual authentication
- Resistant to offline dictionary attacks
- Forward secrecy via ephemeral keys

**Code Entropy Requirements**:
- Interactive use: 16+ bits (2 words)
- Automated/high-security: 24+ bits (3 words)

### 7.3 Relay Security

Relay servers:
- Cannot decrypt traffic (end-to-end encryption)
- Cannot impersonate either party
- Can observe connection metadata (timing, size)
- Can deny service (but cannot compromise security)

### 7.4 WNS Security

**Identity Security**:
- Private key must be kept secret
- Key compromise = identity compromise
- No key recovery mechanism

**TOFU Limitations**:
- First connection vulnerable to MITM
- Mitigations: out-of-band key verification, certificate transparency

**DHT Security**:
- Sybil attacks: mitigated by signature verification
- Eclipse attacks: use multiple bootstrap nodes
- Denial of service: fall back to HTTP/cache

### 7.5 Replay Protection

Advertisements include:
- Timestamp: Must be recent (within 5 minutes)
- Expiry: Short-lived (5 minutes default)
- Signature: Covers all fields including timestamp

### 7.6 Recommendations

1. **Key Storage**: Use OS keychain or hardware security module
2. **Code Communication**: Use secure channel (in-person, encrypted chat)
3. **First Connection**: Verify public key fingerprint if possible
4. **Key Rotation**: Periodically generate new identity if compromised

---

## 8. Implementation Notes

### 8.1 Browser Implementation

For browser-based implementations:

**WebSocket**: Use for mailbox communication
```javascript
const ws = new WebSocket('wss://relay.example.com/v1');
```

**WebRTC**: Use for direct peer connections (instead of TCP)
```javascript
const pc = new RTCPeerConnection(config);
const dc = pc.createDataChannel('wormhole');
```

**Crypto**: Use Web Crypto API + libraries
```javascript
// Ed25519: Use @noble/ed25519
import * as ed from '@noble/ed25519';

// SPAKE2: Implement or use library
// XSalsa20-Poly1305: Use tweetnacl-js
import nacl from 'tweetnacl';
```

**DHT**: Implement Kademlia over WebRTC DataChannels
```javascript
// Each browser is a DHT node
// Bootstrap via well-known WebRTC signaling server
```

### 8.2 Required Libraries

| Function | Recommended Library |
|----------|---------------------|
| Ed25519 | @noble/ed25519, libsodium.js |
| X25519 | @noble/curves, tweetnacl |
| SPAKE2 | Custom implementation |
| XSalsa20-Poly1305 | tweetnacl |
| SHA-256 | Web Crypto API |
| HKDF | @noble/hashes |
| Base32/64 | Built-in or rfc4648 |
| Kademlia | Custom over WebRTC |

### 8.3 Compatibility

Implementations MUST support:
- SPAKE2 with Ed25519 curve
- XSalsa20-Poly1305 for encryption
- Ed25519 for signatures
- SHA-256 for hashing
- HKDF-SHA256 for key derivation

Implementations SHOULD support:
- Multiple transit methods (direct, relay, WebRTC)
- DHT discovery
- HTTP well-known discovery
- Scoped and global names

### 8.4 Test Vectors

See [TEST_VECTORS.md](./TEST_VECTORS.md) for cryptographic test vectors.

---

## Appendix A: Wordlist

The standard wordlist contains 256 words optimized for:
- Phonetic distinctness
- Easy spelling
- Cross-language pronounceability

See [WORDLIST.md](./WORDLIST.md) for the complete list.

---

## Appendix B: References

1. Magic Wormhole: https://magic-wormhole.readthedocs.io/
2. SPAKE2: RFC 9383
3. Ed25519: RFC 8032
4. XSalsa20-Poly1305: https://nacl.cr.yp.to/
5. Kademlia: https://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf
6. HKDF: RFC 5869

---

## Appendix C: Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01 | Initial specification |
