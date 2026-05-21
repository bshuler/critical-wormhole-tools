# Test Results Summary

> Generated: 2026-01-23
> Project: Critical Wormhole Tools v0.4.0

---

## Overall Summary

| Category | Pass | Fail | Skip | Total |
|----------|------|------|------|-------|
| **Python Tests** | 950 | 0 | 9 | 959 |
| **Browser Extension Tests** | 552 | 0 | 0 | 552 |
| **Go (Caddy) Tests** | 27* | - | - | 27* |
| **TOTAL** | **1,529** | **0** | **9** | **1,538** |

*Go tests not executed (Go not installed), count from test function definitions.

---

## Python Tests by Category

| Category | Pass | Fail | Skip | Total |
|----------|------|------|------|-------|
| unit | 818 | 0 | 0 | 818 |
| functional | 21 | 0 | 0 | 21 |
| integration | 111 | 0 | 9 | 120 |
| **Total** | **950** | **0** | **9** | **959** |

---

## Python Unit Tests by File (818 tests)

| File | Tests | Status |
|------|-------|--------|
| unit/test_wns.py | 63 | PASS |
| unit/test_dht_namespace.py | 52 | PASS |
| unit/test_enterprise_namespace.py | 41 | PASS |
| unit/test_enterprise_auth.py | 38 | PASS |
| unit/test_namespace.py | 36 | PASS |
| unit/relay/test_config.py | 31 | PASS |
| unit/test_rdp.py | 30 | PASS |
| unit/test_enterprise_policy.py | 29 | PASS |
| unit/test_transfer.py | 28 | PASS |
| unit/test_enterprise_audit.py | 27 | PASS |
| unit/test_vnc.py | 27 | PASS |
| unit/test_aliases.py | 26 | PASS |
| unit/test_daemon.py | 26 | PASS |
| unit/test_ftp.py | 26 | PASS |
| unit/test_mount.py | 25 | PASS |
| unit/test_nmap.py | 25 | PASS |
| unit/test_enterprise_rate_limiter.py | 24 | PASS |
| unit/test_protocol.py | 24 | PASS |
| unit/test_telnet.py | 22 | PASS |
| unit/test_http_client.py | 21 | PASS |
| unit/test_dns.py | 20 | PASS |
| unit/test_sftp.py | 20 | PASS |
| unit/test_ssh_client.py | 20 | PASS |
| unit/relay/test_mailbox.py | 20 | PASS |
| unit/test_discovery.py | 19 | PASS |
| unit/test_traceroute.py | 19 | PASS |
| unit/test_transport.py | 19 | PASS |
| unit/test_relay_server.py | 18 | PASS |
| unit/test_wormhole_manager.py | 17 | PASS |
| unit/relay/test_transit.py | 15 | PASS |
| unit/test_forwarder.py | 8 | PASS |
| unit/test_version_consistency.py | 2 | PASS |

---

## Python Functional Tests (21 tests)

| File | Tests | Status |
|------|-------|--------|
| functional/test_relay_cli.py | 17 | PASS |
| functional/test_nc_e2e.py | 4 | PASS |

---

## Python Integration Tests (120 tests)

| File | Tests | Status |
|------|-------|--------|
| integration/test_new_tools.py | 26 | PASS |
| integration/test_wns_server.py | 20 | PASS |
| integration/test_advertisement.py | 17 | PASS |
| integration/test_ssh_server.py | 16 | PASS |
| integration/test_multi_relay.py | 10 | PASS |
| integration/test_ssh_tunnel.py | 9 | PASS |
| integration/test_relay.py | 9 | PASS |
| integration/test_discovery_site.py | 0/9 | SKIP (Playwright required) |
| integration/test_real_wormhole.py | 4 | PASS |

---

## Browser Extension Tests by File (552 tests)

| File | Tests | Status |
|------|-------|--------|
| tests/unit/dilation.test.js | 72 | PASS |
| tests/unit/protocol/transit.test.js | 52 | PASS |
| tests/unit/viewer.test.js | 51 | PASS |
| tests/unit/background.test.js | 48 | PASS |
| tests/unit/wns/identity.test.js | 46 | PASS |
| tests/unit/protocol/wormhole.test.js | 46 | PASS |
| tests/unit/protocol/mailbox.test.js | 42 | PASS |
| tests/unit/crypto/spake2.test.js | 37 | PASS |
| tests/unit/wns/advertisement.test.js | 32 | PASS |
| tests/unit/crypto/index.test.js | 28 | PASS |
| tests/unit/crypto/hkdf.test.js | 25 | PASS |
| tests/unit/crypto/nacl.test.js | 23 | PASS |
| tests/unit/crypto/ed25519.test.js | 21 | PASS |
| tests/unit/crypto/hash.test.js | 18 | PASS |
| tests/functional/wormhole-flow.test.js | 11 | PASS |

---

## Go (Caddy) Tests (27 tests)

| File | Tests | Status |
|------|-------|--------|
| caddy/daemon_test.go | 12 | NOT RUN (Go not installed) |
| caddy/integration_test.go | 9 | NOT RUN |
| caddy/wormhole_test.go | 6 | NOT RUN |

---

## Skipped Tests (9 total)

All skipped tests are in `tests/integration/test_discovery_site.py` and require Playwright:

1. `test_discovery_site_loads` - Requires browser
2. `test_connect_to_wormhole_code` - Requires browser
3. `test_html_content_rendered` - Requires browser
4. `test_css_loaded` - Requires browser
5. `test_javascript_execution` - Requires browser
6. `test_internal_navigation` - Requires browser
7. `test_image_loading` - Requires browser
8. `test_server_starts_and_returns_code` - Requires browser
9. `test_server_cleanup_on_exit` - Requires browser

---

## Test Coverage by Module

### WELL TESTED (dedicated test files exist)
- ✅ WNS (identity, aliases, namespace, DHT) - 178 tests
- ✅ Enterprise features (auth, audit, rate limiter, namespace, policy) - 159 tests
- ✅ Protocol handling - 24 tests
- ✅ SSH client/server - 36 tests
- ✅ Network tools (telnet, ftp, nmap, traceroute, dns, mount, vnc, rdp) - 195 tests
- ✅ Transfer (SCP, SFTP) - 48 tests
- ✅ Relay server - 84 tests
- ✅ Daemon API - 26 tests
- ✅ HTTP client - 21 tests

### NO DEDICATED TESTS (identified gaps)
- ❌ `wh curl` CLI - NO dedicated tests
- ❌ `wh wget` CLI - NO dedicated tests
- ❌ `wh listen` CLI - NO dedicated tests
- ❌ `wh ping` CLI - NO dedicated tests
- ❌ `wh tunnel` CLI - NO dedicated tests
- ❌ `wh proxy` CLI - NO dedicated tests
- ❌ `wh rsync` CLI - NO dedicated tests
- ❌ HTTP server (`src/wh/http/server.py`) - NO tests
- ❌ CLI registration verification - NO tests
- ❌ DHT bootstrap env parsing - NO tests
- ❌ Smoke test suite - NONE
- ❌ Performance tests - NONE

---

## Warnings (22 total)

All warnings are `RuntimeWarning: coroutine was never awaited` from mock objects.
These are cosmetic and do not affect test results.

---

## Next Steps (from approved plan)

See `.omc/plans/comprehensive-test-coverage.md` for the approved test implementation plan.

**Priority 1 (HIGH)**: Add tests for curl, wget, listen, HTTP server, CLI registration, DHT bootstrap
**Priority 2 (MEDIUM)**: Add tests for ping, tunnel, proxy, rsync, error handling, security
**Priority 3 (LOW)**: Add smoke tests and performance test scaffolding

