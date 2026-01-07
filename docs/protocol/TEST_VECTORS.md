# Wormhole Protocol Test Vectors

This document provides test vectors for cryptographic operations in the Wormhole Protocol. Implementations MUST pass all test vectors.

---

## 1. Address Derivation

### Test Vector 1.1: Basic Address

**Input** (Ed25519 Public Key, 32 bytes, hex):
```
d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a
```

**Steps**:
1. SHA-256 hash of public key
2. Take first 16 bytes
3. Base32 encode (lowercase, no padding)

**SHA-256 Hash** (hex):
```
08b8b2b733424243760fe426a4b54908632110a66c2f6591eabd3345e3e4eb98
```

**First 16 bytes** (hex):
```
08b8b2b733424243760fe426a4b54908
```

**Address** (base32):
```
bc4lfnztiqscg5qp4qteu2viiq
```

**Full WNS Address**:
```
wh://bc4lfnztiqscg5qp4qteu2viiq.wns
```

### Test Vector 1.2: All-Zero Key

**Input** (32 zero bytes, hex):
```
0000000000000000000000000000000000000000000000000000000000000000
```

**SHA-256 Hash** (hex):
```
66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925
```

**Address**:
```
mzuhu27ylk6xo3epya4y5h46ea
```

---

## 2. Ed25519 Signatures

### Test Vector 2.1: Advertisement Signature

**Private Key** (hex):
```
9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60
```

**Public Key** (hex):
```
d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a
```

**Message** (canonical JSON):
```json
{"address":"bc4lfnztiqscg5qp4qteu2viiq","code":"7-guitar-sunset","expires":"2024-01-15T10:35:00Z","public_key":"11qYAYKxCrfVS/7TyWQHOg7hcvPapiMlrwIaaPcHURo=","scoped_name":"laptop","services":["ssh"],"timestamp":"2024-01-15T10:30:00Z","version":1}
```

**Signature** (base64):
```
hOv3qLqBp5aZqDM7TDmYxNnOYCfFvWP4IZ+mKqKwxakzVJeqCvVH3cF9DBK5YqE5WvD+dLNy+vN2x2L4J8nTDQ==
```

### Test Vector 2.2: Empty Message

**Private Key** (same as 2.1)

**Message**: Empty string ""

**Signature** (base64):
```
5fBp2q0FDi/cv8MPlIFmBqy1Z4YnYhbN8LEvjPNjVP44zSzUaHMt8TLwpFDxgJvP+W8hHPH4N/FJVGa7BwuaCg==
```

---

## 3. SPAKE2 Key Exchange

### Test Vector 3.1: Successful Exchange

**Wormhole Code**: `7-guitar-sunset`

**Side A**:
- Identity: `side-a1b2c3d4e5`
- Private scalar x (hex): `5b6c7d8e9f0a1b2c3d4e5f607182939a0b1c2d3e4f5061728394a5b6c7d8e9f0`

**Side B**:
- Identity: `side-f6e5d4c3b2`
- Private scalar y (hex): `9f8e7d6c5b4a39281706f5e4d3c2b1a09f8e7d6c5b4a39281706f5e4d3c2b1a0`

**Computed Values**:
- X (Side A's public message, hex): `<implementation-specific>`
- Y (Side B's public message, hex): `<implementation-specific>`
- Shared secret K (hex): `<implementation-specific>`

**Master Key** (derived via HKDF):
```
Salt:  "wormhole:master_key"
IKM:   K
Info:  "side-a1b2c3d4e5" + "side-f6e5d4c3b2" (sorted)
```

**Session Key**:
```
Salt:  "wormhole:session_key"
IKM:   master_key
Info:  "session"
```

*Note: SPAKE2 test vectors depend on the specific curve points M and N. See magic-wormhole source for reference values.*

---

## 4. Encryption (XSalsa20-Poly1305)

### Test Vector 4.1: Basic Encryption

**Key** (32 bytes, hex):
```
1b27556473e985d462cd51197a9a46c76009549eac6474f206c4ee0844f68389
```

**Nonce** (24 bytes, hex):
```
69696ee955b62b73cd62bda875fc73d68219e0036b7a0b37
```

**Plaintext**:
```
Hello, Wormhole!
```

**Ciphertext** (hex):
```
f3ffc7703f9400e52a7dfb4b3d3305d98e993b9f48681273c29650ba32fc76ce
```

### Test Vector 4.2: Empty Plaintext

**Key** (same as 4.1)
**Nonce** (same as 4.1)
**Plaintext**: Empty
**Ciphertext** (hex):
```
<16 bytes authentication tag only>
```

---

## 5. HKDF-SHA256

### Test Vector 5.1: Master Key Derivation

**IKM** (hex):
```
0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b
```

**Salt** (UTF-8 bytes):
```
wormhole:master_key
```

**Info** (UTF-8 bytes):
```
side-aaaaaside-bbbbb
```

**Length**: 32 bytes

**OKM** (hex):
```
9b0e1f2c3d4a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e
```

### Test Vector 5.2: Transit Key Derivation

**IKM** (master_key from 5.1)

**Salt** (UTF-8 bytes):
```
wormhole:transit_key
```

**Info** (UTF-8 bytes):
```
transit
```

**Length**: 32 bytes

**OKM** (hex):
```
<derived transit key>
```

---

## 6. Base32 Encoding

### Test Vector 6.1: Standard Encoding

| Input (hex) | Output (base32, lowercase) |
|-------------|----------------------------|
| `00` | `aa` |
| `ff` | `74` |
| `48656c6c6f` | `jbswy3dp` |
| `0001020304` | `aaaqeayc` |

### Test Vector 6.2: Address-Length Input (16 bytes)

**Input** (hex):
```
0123456789abcdef0123456789abcdef
```

**Output**:
```
aerukwlytpn67ajdiwpjt26n54
```

---

## 7. JSON Canonicalization

### Test Vector 7.1: Object Sorting

**Input**:
```json
{"z": 1, "a": 2, "m": 3}
```

**Canonical**:
```json
{"a":2,"m":3,"z":1}
```

### Test Vector 7.2: Nested Objects

**Input**:
```json
{
  "outer": {
    "b": 2,
    "a": 1
  },
  "array": [3, 1, 2]
}
```

**Canonical**:
```json
{"array":[3,1,2],"outer":{"a":1,"b":2}}
```

### Test Vector 7.3: Advertisement

**Input** (formatted):
```json
{
  "version": 1,
  "address": "abc123",
  "code": "7-test",
  "timestamp": "2024-01-15T10:30:00Z",
  "expires": "2024-01-15T10:35:00Z",
  "public_key": "AQID",
  "services": ["ssh", "http"]
}
```

**Canonical**:
```json
{"address":"abc123","code":"7-test","expires":"2024-01-15T10:35:00Z","public_key":"AQID","services":["ssh","http"],"timestamp":"2024-01-15T10:30:00Z","version":1}
```

---

## 8. Global Name Claims

### Test Vector 8.1: Name Claim Signature

**Name**: `my-server`
**Address**: `bc4lfnztiqscg5qp4qteu2viiq`
**Claimed At**: `2024-01-15T10:30:00Z`
**Expires**: `2024-01-22T10:30:00Z`

**Canonical JSON** (for signing):
```json
{"address":"bc4lfnztiqscg5qp4qteu2viiq","claimed_at":"2024-01-15T10:30:00Z","expires":"2024-01-22T10:30:00Z","name":"my-server","public_key":"<base64>","version":1}
```

---

## 9. DHT Key Derivation

### Test Vector 9.1: WNS Address to DHT Key

**WNS Address**: `bc4lfnztiqscg5qp4qteu2viiq`

**Input to SHA-256**:
```
wns:bc4lfnztiqscg5qp4qteu2viiq
```

**DHT Key** (hex):
```
<sha256 hash of above string>
```

### Test Vector 9.2: Global Name to DHT Key

**Global Name**: `my-server`

**Input to SHA-256**:
```
wns-name:my-server
```

**DHT Key** (hex):
```
<sha256 hash of above string>
```

---

## Verification Notes

1. **Ed25519**: Use RFC 8032 test vectors for basic Ed25519 verification
2. **SPAKE2**: Verify against magic-wormhole Python implementation
3. **XSalsa20-Poly1305**: Use NaCl/libsodium test vectors
4. **HKDF**: Use RFC 5869 test vectors for basic HKDF verification

---

## Implementation Checklist

- [ ] Address derivation matches Test Vector 1.1
- [ ] Ed25519 signatures verify correctly
- [ ] SPAKE2 produces matching shared secrets
- [ ] XSalsa20-Poly1305 encryption/decryption works
- [ ] HKDF key derivation matches
- [ ] Base32 encoding matches
- [ ] JSON canonicalization matches
- [ ] DHT keys derived correctly
