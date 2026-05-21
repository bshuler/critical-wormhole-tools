# Work Plan: Comprehensive Test Coverage

> **Generated**: 2026-01-23
> **Project**: Critical Wormhole Tools (CWT)
> **Current Version**: 0.4.0
> **Scope**: Complete test coverage for all untested modules and CLI commands
> **Plan Version**: 1.1 (Revised based on Critic/Architect feedback)

---

## Context

### Original Request
Create comprehensive test coverage for Critical Wormhole Tools, addressing all identified gaps in unit, functional, integration, E2E, and smoke tests.

### Current State Analysis

**Test Inventory:**
- 959 Python tests with ~44% overall coverage
- 552 browser extension tests
- Test structure: `tests/unit/`, `tests/functional/`, `tests/integration/`

**Test Patterns Used:**
- Pytest with pytest-asyncio for async tests
- Click CliRunner for CLI command testing
- MagicMock/AsyncMock for wormhole manager and protocols
- In-memory transports for protocol testing
- Fixtures in `conftest.py` for common mocks

### Gap Analysis

| Category | Module | Current State | Priority |
|----------|--------|---------------|----------|
| CLI | `wh curl` | NO dedicated tests | HIGH |
| CLI | `wh wget` | NO dedicated tests | HIGH |
| CLI | `wh listen` | NO dedicated tests | HIGH |
| HTTP | `src/wh/http/server.py` | NO tests, has binary file bug | HIGH |
| CLI | Main CLI registration | Partial (help only) | HIGH |
| DHT | Bootstrap/env var parsing | NO tests | HIGH |
| CLI | `wh ping` | NO dedicated tests | MEDIUM |
| CLI | `wh tunnel` | NO dedicated tests | MEDIUM |
| CLI | `wh proxy` | NO dedicated tests | MEDIUM |
| CLI | `wh rsync` | NO dedicated tests | MEDIUM |
| WNS | CLI commands (identity: 13, alias: 5) | Partial - needs all 18 subcommands | MEDIUM |
| Security | Path traversal, injection | Limited | MEDIUM |
| Error | Network failures, timeouts | Limited | MEDIUM |
| Smoke | Quick validation suite | Non-existent | LOW |
| Performance | Large files, connections | Non-existent | LOW |

### Out-of-Scope

| Item | Reason | Reference |
|------|--------|-----------|
| Caddy E2E Tests | Separate work item; existing Go tests in `caddy-wh/` provide sufficient coverage | See `caddy-wh/*_test.go` |

---

## Work Objectives

### Core Objective
Achieve comprehensive test coverage across all wh CLI commands and modules, with particular focus on previously untested critical functionality.

### Deliverables
1. Unit tests for all untested modules
2. Functional tests for all CLI commands
3. Integration tests for multi-component workflows
4. E2E tests for full feature scenarios
5. Smoke test suite for CI/CD validation
6. Security-focused test cases

### Definition of Done
- All new test files created and passing
- Each test category has specific acceptance criteria met
- Tests follow existing patterns from `conftest.py`
- Tests are organized in appropriate directories
- Coverage increased for each targeted module

---

## Guardrails

### Must Have
- Tests use existing mock patterns from conftest.py
- Async tests properly use pytest-asyncio
- CLI tests use Click's CliRunner
- Tests are isolated (no network dependency for unit tests)
- Each test function has descriptive name and docstring

### Must NOT Have
- Tests that require real network connections (except integration marked tests)
- Flaky tests dependent on timing
- Tests that modify global state without cleanup
- Hardcoded paths or platform-specific assumptions

---

## Task Flow and Dependencies

```
Phase 1: HIGH Priority - Core Missing Tests
    |
    v
Phase 2: MEDIUM Priority - Network Tools
    |
    v
Phase 3: MEDIUM Priority - Error & Security
    |
    v
Phase 4: LOW Priority - Smoke & Performance
```

---

## Phase 1: HIGH Priority - Core Missing Tests

### Task 1.1: HTTP Server Unit Tests

**File**: `tests/unit/test_http_server.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_http_file_server_init` | Test HTTPFileServer initialization | Server initializes with valid directory |
| `test_http_file_server_init_invalid_dir` | Test init with invalid directory | Raises ValueError for non-directory |
| `test_handle_http_request_get_file` | Test GET request for existing file | Returns 200 with file content |
| `test_handle_http_request_index_html` | Test GET / serves index.html | Returns index.html content |
| `test_handle_http_request_html_extension` | Test path without .html extension | Adds .html extension automatically |
| `test_handle_http_request_directory_index` | Test GET /subdir/ serves index.html | Returns subdir/index.html |
| `test_handle_http_request_404` | Test GET for non-existent file | Returns 404 Not Found |
| `test_handle_http_request_path_traversal` | Test path traversal prevention | Returns 403 Forbidden |
| `test_handle_http_request_invalid_type` | Test unknown request type | Returns 400 Bad Request |
| `test_handle_http_request_invalid_json` | Test malformed JSON request | Returns 400 with error |
| `test_send_response_json` | Test JSON response serialization | Valid JSON response sent |
| `test_send_error_response` | Test error response format | HTML error body returned |
| `test_content_type_detection` | Test MIME type guessing | Correct Content-Type headers |
| `test_binary_file_handling` | Test binary file triggers 500 error | UnicodeDecodeError causes 500 (KNOWN BUG) |

**Implementation Notes:**
- Mock `wormhole_manager` with `receive_message` and `send_message`
- Use `tmp_path` fixture for test directory
- Test with various file types (.html, .css, .js, .json)

**KNOWN BUG - Binary File Handling:**
- Current code at line 144 uses `file_path.read_text(encoding='utf-8')`
- Binary files (images, PDFs, etc.) cause UnicodeDecodeError
- This results in 500 Internal Server Error
- Test should verify this current (broken) behavior
- Bug fix is OUT OF SCOPE for test coverage work - create separate issue

---

### Task 1.2: DHT Bootstrap Unit Tests

**File**: `tests/unit/test_dht_bootstrap.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_parse_bootstrap_nodes_env_empty` | Test with no env var | Returns empty list |
| `test_parse_bootstrap_nodes_env_single` | Test with single node | Parses host:port correctly |
| `test_parse_bootstrap_nodes_env_multiple` | Test comma-separated nodes | All nodes parsed |
| `test_parse_bootstrap_nodes_env_invalid_format` | Test invalid format (no port) | Skipped gracefully |
| `test_parse_bootstrap_nodes_env_invalid_port` | Test non-numeric port | Skipped gracefully |
| `test_use_public_bootstrap_env_true` | Test WH_DHT_USE_PUBLIC_BOOTSTRAP=true | Returns True |
| `test_use_public_bootstrap_env_false` | Test WH_DHT_USE_PUBLIC_BOOTSTRAP=false | Returns False |
| `test_use_public_bootstrap_env_unset` | Test with no env var | Returns False (default) |
| `test_use_public_bootstrap_env_case_insensitive` | Test TRUE, True, 1, yes | All return True |
| `test_fetch_bootstrap_nodes_success` | Test HTTP fetch with mock | Nodes returned from JSON |
| `test_fetch_bootstrap_nodes_timeout` | Test HTTP timeout | Graceful failure, empty list |
| `test_fetch_bootstrap_nodes_invalid_json` | Test malformed JSON response | Graceful failure |
| `test_fetch_bootstrap_nodes_empty_response` | Test empty JSON array | Returns empty list |
| `test_get_bootstrap_nodes_env_priority` | Test env nodes come first | Env nodes before fetched |
| `test_get_bootstrap_nodes_deduplication` | Test duplicate nodes filtered | No duplicates in result |

**Implementation Notes:**
- Use `monkeypatch` fixture to set/unset environment variables
- Mock `aiohttp.ClientSession` for HTTP fetch tests
- Test `parse_bootstrap_nodes_env()`, `use_public_bootstrap_env()`, `fetch_bootstrap_nodes()`
- Located in `src/wh/wns/dht.py`

---

### Task 1.3: wh curl Unit Tests

**File**: `tests/unit/test_curl.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_curl_command_help` | Test --help output | Shows usage, options, examples |
| `test_curl_parse_headers_single` | Test single header parsing | Header dict populated |
| `test_curl_parse_headers_multiple` | Test multiple headers | All headers in dict |
| `test_curl_parse_headers_invalid` | Test header without colon | Ignored gracefully |
| `test_curl_data_string` | Test -d flag with string | Body encoded as bytes |
| `test_curl_data_binary` | Test --data-binary with file | File contents read |
| `test_curl_output_to_file` | Test -o flag | Response written to file |
| `test_curl_include_headers` | Test -i flag | Headers in output |
| `test_curl_verbose_mode` | Test -v flag | Request/response logged |
| `test_curl_silent_mode` | Test -s flag | No progress output |
| `test_curl_method_options` | Test -X with various methods | POST, PUT, DELETE work |

---

### Task 1.4: wh wget Unit Tests

**File**: `tests/unit/test_wget.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_wget_command_help` | Test --help output | Shows usage, options |
| `test_wget_filename_from_url` | Test filename extraction | Correct filename parsed |
| `test_wget_filename_fallback` | Test empty path URL | Falls back to index.html |
| `test_wget_output_to_file` | Test -O flag | Saves to specified file |
| `test_wget_output_to_stdout` | Test -O - flag | Writes to stdout |
| `test_wget_directory_prefix` | Test -P flag | Saves to directory |
| `test_wget_quiet_mode` | Test -q flag | No output except errors |
| `test_wget_custom_headers` | Test --header flag | Headers sent in request |
| `test_wget_http_error` | Test non-200 response | ClickException raised |

---

### Task 1.5: wh listen Unit Tests

**File**: `tests/unit/test_listen.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_listen_command_help` | Test --help output | Shows all modes and options |
| `test_listen_port_forward_mode` | Test -p flag setup | Port forward initialized |
| `test_listen_ssh_mode` | Test --ssh flag | SSH server handler used |
| `test_listen_http_mode` | Test --http flag | HTTP proxy handler used |
| `test_listen_serve_mode` | Test --serve flag | File server initialized |
| `test_listen_custom_code` | Test --code flag | Uses provided code |
| `test_listen_auth_pubkey` | Test --auth-method=pubkey | Authenticator created |
| `test_listen_auth_ldap` | Test --auth-method=ldap | LDAP authenticator used |
| `test_listen_auth_pubkey_no_keys` | Test pubkey without keys file | ClickException raised |
| `test_listen_audit_logging` | Test --audit-log flag | AuditLogger initialized |
| `test_listen_dilation_timeout` | Test dilation fallback | Falls back after timeout |
| `test_listen_no_dilation` | Test --no-dilate flag | Skips dilation |

---

### Task 1.6: CLI Registration Tests

**File**: `tests/unit/test_cli_registration.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_all_commands_registered` | Verify all commands in CLI | 25 commands registered |
| `test_cli_help_lists_commands` | Check help output | All command names shown |
| `test_cli_version` | Test --version flag | Shows version number |
| `test_cli_relay_option` | Test --relay option | Passed to context |
| `test_cli_transit_option` | Test --transit option | Overrides relay |
| `test_cli_code_length_option` | Test -c flag | Sets code length |
| `test_cli_verbose_option` | Test -v flag | Increases verbosity |
| `test_cli_namespace_option` | Test -n flag | Sets namespace |
| `test_resolve_relay_default` | Test default relay resolution | Uses config default |
| `test_resolve_relay_by_name` | Test relay by name | Looks up in config |
| `test_resolve_relay_by_url` | Test relay by URL | Uses URL directly |

**Commands to verify registration (25 total):**
```python
EXPECTED_COMMANDS = [
    'nc', 'listen', 'ssh', 'scp', 'sftp', 'curl', 'wget',
    'ping', 'tunnel', 'proxy', 'rsync', 'serve', 'daemon', 'relay',
    'telnet', 'ftp', 'nmap', 'traceroute', 'dns', 'mount', 'vnc', 'rdp',
    'identity', 'alias', 'namespace'
]  # Total: 25 commands
```

---

### Task 1.7: wh curl/wget Functional Tests

**File**: `tests/functional/test_http_commands.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_curl_cli_requires_code` | Test curl without --code | Error message shown |
| `test_curl_cli_requires_url` | Test curl without URL | Error message shown |
| `test_wget_cli_requires_code` | Test wget without --code | Error message shown |
| `test_wget_cli_requires_url` | Test wget without URL | Error message shown |
| `test_curl_with_mock_manager` | Test curl with mocked wormhole | HTTP request made |
| `test_wget_with_mock_manager` | Test wget with mocked wormhole | File downloaded |

---

### Task 1.8: wh listen Functional Tests

**File**: `tests/functional/test_listen.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_listen_generates_code` | Test code generation | Code displayed |
| `test_listen_port_forward_setup` | Test port forward initialization | Forwarder created |
| `test_listen_ssh_server_setup` | Test SSH server mode | SSH handler active |
| `test_listen_http_proxy_setup` | Test HTTP proxy mode | HTTP handler active |
| `test_listen_file_server_setup` | Test --serve mode | File server active |

---

## Phase 2: MEDIUM Priority - Network Tools

### Task 2.1: wh ping Unit Tests

**File**: `tests/unit/test_ping.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_ping_protocol_init` | Test PingProtocol initialization | All fields set correctly |
| `test_ping_make_packet` | Test packet creation | Correct format and size |
| `test_ping_parse_packet` | Test packet parsing | Type, seq, timestamp extracted |
| `test_ping_parse_packet_too_short` | Test short packet | Returns None |
| `test_ping_server_replies` | Test server echo behavior | Reply sent for request |
| `test_ping_client_tracks_rtt` | Test RTT calculation | RTT stored in list |
| `test_ping_statistics` | Test statistics calculation | min/avg/max/stddev correct |
| `test_ping_packet_loss` | Test loss calculation | Percentage correct |
| `test_ping_timeout_handling` | Test timeout | Pending removed, timeout logged |
| `test_ping_custom_size` | Test -s flag | Larger packet created |
| `test_ping_custom_count` | Test -c flag | Correct number sent |
| `test_ping_custom_interval` | Test -i flag | Interval respected |

---

### Task 2.2: wh tunnel Unit Tests

**File**: `tests/unit/test_tunnel.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_parse_forward_spec_simple` | Test port:port format | Localhost assumed |
| `test_parse_forward_spec_full` | Test port:host:port format | All parts parsed |
| `test_parse_forward_spec_invalid` | Test invalid format | ValueError raised |
| `test_tunnel_protocol_init` | Test TunnelProtocol init | All fields initialized |
| `test_tunnel_send_message` | Test message serialization | Correct header format |
| `test_tunnel_open_channel` | Test channel open request | Open message sent |
| `test_tunnel_handle_data` | Test data forwarding | Data written to channel |
| `test_tunnel_handle_close` | Test channel close | Writer closed, removed |
| `test_local_forwarder_init` | Test LocalForwarder init | All params stored |
| `test_local_forwarder_start` | Test server start | Listening on port |

---

### Task 2.3: wh proxy Unit Tests

**File**: `tests/unit/test_proxy.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_proxy_protocol_init` | Test ProxyProtocol init | All fields initialized |
| `test_proxy_send_message` | Test message format | Header + channel + length |
| `test_proxy_connect_request` | Test connection request | Connect message sent |
| `test_proxy_handle_data` | Test data forwarding | Data written |
| `test_socks5_server_init` | Test Socks5Server init | Port and host set |
| `test_socks5_greeting` | Test SOCKS5 handshake | No auth selected |
| `test_socks5_connect_ipv4` | Test IPv4 address parsing | Address extracted |
| `test_socks5_connect_domain` | Test domain parsing | Domain extracted |
| `test_socks5_connect_ipv6` | Test IPv6 address parsing | Address extracted |
| `test_socks5_unsupported_cmd` | Test BIND/UDP commands | Not supported reply |
| `test_socks5_connection_failure` | Test connect failure | Host unreachable reply |

---

### Task 2.4: wh rsync Unit Tests

**File**: `tests/unit/test_rsync.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_file_checksum` | Test MD5 checksum | Correct hash returned |
| `test_scan_directory` | Test directory scanning | Manifest generated |
| `test_scan_directory_recursive` | Test recursive scan | All files found |
| `test_compare_manifests_new_file` | Test new file detection | File in to_send |
| `test_compare_manifests_changed` | Test changed file | File in to_send |
| `test_compare_manifests_unchanged` | Test unchanged file | Not in to_send |
| `test_compare_manifests_delete` | Test delete mode | Files in to_delete |
| `test_rsync_protocol_init` | Test RsyncProtocol init | State initialized |
| `test_rsync_send_manifest` | Test manifest sending | JSON serialized |
| `test_rsync_file_transfer` | Test file chunk handling | Data written |
| `test_rsync_file_end` | Test file completion | Handle closed |

---

### Task 2.5: Network Tools Functional Tests

**File**: `tests/functional/test_network_tools.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_ping_cli_listen_mode` | Test wh ping -l | Code generated |
| `test_ping_cli_client_mode` | Test wh ping CODE | Stats displayed |
| `test_tunnel_cli_listen_mode` | Test wh tunnel -l | Code generated |
| `test_tunnel_cli_local_forward` | Test wh tunnel -L | Forward active |
| `test_proxy_cli_listen_mode` | Test wh proxy -l | Code generated |
| `test_proxy_cli_client_mode` | Test wh proxy CODE | SOCKS5 listening |
| `test_rsync_cli_listen_mode` | Test wh rsync -l | Ready to receive |
| `test_rsync_cli_dry_run` | Test wh rsync -n | Shows what would transfer |

---

## Phase 3: MEDIUM Priority - Error & Security Tests

### Task 3.1: Error Handling Tests

**File**: `tests/unit/test_error_handling.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_wormhole_manager_connection_timeout` | Test connection timeout | Proper exception raised |
| `test_wormhole_manager_dilation_failure` | Test dilation failure | Fallback or error |
| `test_http_client_timeout` | Test HTTP request timeout | Timeout exception |
| `test_http_server_connection_lost` | Test sudden disconnect | Clean shutdown |
| `test_ssh_connection_refused` | Test SSH connect failure | Error message shown |
| `test_forwarder_port_in_use` | Test port already bound | Clear error message |
| `test_transfer_file_not_found` | Test missing file | File not found error |
| `test_transfer_permission_denied` | Test unreadable file | Permission error |
| `test_relay_connection_refused` | Test relay unreachable | Connection error |
| `test_invalid_wormhole_code` | Test malformed code | Validation error |

---

### Task 3.2: Security Tests

**File**: `tests/unit/test_security.py`

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_http_server_path_traversal_dotdot` | Test ../../../etc/passwd | Forbidden returned |
| `test_http_server_path_traversal_encoded` | Test %2e%2e%2f encoded | Forbidden returned |
| `test_http_server_symlink_escape` | Test symlink outside root | Forbidden returned |
| `test_ftp_path_traversal` | Test FTP path escape | Access denied |
| `test_mount_path_traversal` | Test mount path escape | EACCES error |
| `test_ssh_command_injection` | Test shell metacharacters | Properly escaped |
| `test_auth_invalid_pubkey` | Test invalid public key | Auth rejected |
| `test_auth_invalid_password` | Test wrong password | Auth rejected |
| `test_rate_limiter_throttle` | Test rate limiting | Request blocked |
| `test_namespace_isolation` | Test namespace crossing | Access denied |

---

### Task 3.3: WNS CLI Tests

**File**: `tests/functional/test_wns_cli.py`

**Coverage:** All 18 subcommands (13 identity + 5 alias)

**Identity Subcommand Tests (13 commands):**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_identity_create` | Test wh identity create | Key pair generated, stored |
| `test_identity_list` | Test wh identity list | All identities shown with markers |
| `test_identity_default` | Test wh identity default | Shows current default identity |
| `test_identity_set_default` | Test wh identity set-default NAME | Default changed |
| `test_identity_clear_default` | Test wh identity clear-default | Default cleared |
| `test_identity_show` | Test wh identity show NAME | Identity details displayed |
| `test_identity_delete` | Test wh identity delete NAME | Identity removed |
| `test_identity_export` | Test wh identity export NAME | Public key output to stdout |
| `test_identity_set_name` | Test wh identity set-name ID NAME | Local name updated |
| `test_identity_claim_name` | Test wh identity claim-name NAME | WNS name registration |
| `test_identity_list_names` | Test wh identity list-names | All claimed names shown |
| `test_identity_release_name` | Test wh identity release-name NAME | WNS name released |
| `test_identity_import` | Test wh identity import FILE | Identity imported from file |

**Alias Subcommand Tests (5 commands):**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_alias_add` | Test wh alias add NAME TARGET | Alias stored locally |
| `test_alias_remove` | Test wh alias remove NAME | Alias deleted |
| `test_alias_list` | Test wh alias list | All aliases shown |
| `test_alias_show` | Test wh alias show NAME | Single alias details |
| `test_alias_resolve` | Test wh alias resolve NAME | Target resolved (local or WNS) |

**Additional WNS Integration Tests:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_wns_url_resolution` | Test wh:// URL resolution | Code returned from name |
| `test_alias_resolve_fallback_wns` | Test local miss, WNS hit | Falls back to WNS lookup |
| `test_identity_create_with_name` | Test create with --name flag | Identity created with local name |

---

## Phase 4: LOW Priority - Smoke & Performance

### Task 4.1: Smoke Test Suite

**File**: `tests/smoke/test_smoke.py`

**Purpose**: Quick validation for CI/CD - should complete in <30 seconds

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_cli_loads` | Test CLI can be imported | No import errors |
| `test_all_commands_exist` | Test all commands accessible | Help works for all |
| `test_version_number` | Test version is set | Non-empty version |
| `test_relay_config_loads` | Test relay config readable | Config parsed |
| `test_identity_manager_loads` | Test identity manager init | Manager created |
| `test_http_client_imports` | Test HTTP module imports | No import errors |
| `test_ssh_module_imports` | Test SSH module imports | No import errors |
| `test_enterprise_modules_load` | Test enterprise imports | Modules accessible |

**Configuration**:
```python
# pytest.ini or conftest.py marker
pytest.mark.smoke  # Run with: pytest -m smoke
```

---

### Task 4.2: Performance Test Scaffolding

**File**: `tests/performance/test_performance.py`

**Purpose**: Baseline performance tests (marked as slow, not run in CI)

**Test Cases:**

| Test Function | Description | Acceptance Criteria |
|---------------|-------------|---------------------|
| `test_large_file_checksum` | Test 100MB file MD5 | Completes in <5s |
| `test_manifest_scan_1000_files` | Test large directory scan | Completes in <10s |
| `test_concurrent_channels` | Test 100 tunnel channels | No memory leak |
| `test_http_response_throughput` | Test response rate | >1000 req/s locally |
| `test_rsync_incremental_scan` | Test 10000 file manifest | Completes in <30s |

**Configuration**:
```python
pytest.mark.slow  # Run with: pytest -m slow
```

---

## Verification Steps

### For Each Phase

1. **Create test files** in correct directory
2. **Run tests** with: `pytest tests/unit/test_<module>.py -v`
3. **Check coverage**: `pytest --cov=wh --cov-report=html tests/`
4. **Verify no regressions**: `pytest tests/`

### Final Verification

```bash
# Run all new tests
pytest tests/unit/test_http_server.py \
       tests/unit/test_dht_bootstrap.py \
       tests/unit/test_curl.py \
       tests/unit/test_wget.py \
       tests/unit/test_listen.py \
       tests/unit/test_cli_registration.py \
       tests/unit/test_ping.py \
       tests/unit/test_tunnel.py \
       tests/unit/test_proxy.py \
       tests/unit/test_rsync.py \
       tests/unit/test_error_handling.py \
       tests/unit/test_security.py \
       tests/functional/test_http_commands.py \
       tests/functional/test_listen.py \
       tests/functional/test_network_tools.py \
       tests/functional/test_wns_cli.py \
       tests/smoke/test_smoke.py \
       -v --tb=short

# Check coverage improvement
pytest --cov=wh --cov-report=term-missing tests/

# Expected: >60% overall coverage (up from ~44%)
```

---

## Commit Strategy

### Commit 1: Phase 1 - Core HTTP and DHT tests
```
test: Add HTTP server, DHT bootstrap, and curl/wget unit tests

- Add tests/unit/test_http_server.py (14 tests)
- Add tests/unit/test_dht_bootstrap.py (15 tests)
- Add tests/unit/test_curl.py (11 tests)
- Add tests/unit/test_wget.py (9 tests)
- Add tests/functional/test_http_commands.py (6 tests)
```

### Commit 2: Phase 1 - Listen and CLI tests
```
test: Add listen command and CLI registration tests

- Add tests/unit/test_listen.py (12 tests)
- Add tests/unit/test_cli_registration.py (11 tests)
- Add tests/functional/test_listen.py (5 tests)
```

### Commit 3: Phase 2 - Network tools tests
```
test: Add network tools unit and functional tests

- Add tests/unit/test_ping.py (12 tests)
- Add tests/unit/test_tunnel.py (10 tests)
- Add tests/unit/test_proxy.py (11 tests)
- Add tests/unit/test_rsync.py (11 tests)
- Add tests/functional/test_network_tools.py (8 tests)
```

### Commit 4: Phase 3 - Error, security, and WNS CLI tests
```
test: Add error handling, security, and complete WNS CLI tests

- Add tests/unit/test_error_handling.py (10 tests)
- Add tests/unit/test_security.py (10 tests)
- Add tests/functional/test_wns_cli.py (21 tests - all 18 subcommands + 3 integration)
```

### Commit 5: Phase 4 - Smoke and performance scaffolds
```
test: Add smoke test suite and performance test scaffolding

- Add tests/smoke/test_smoke.py (8 tests)
- Add tests/performance/test_performance.py (5 tests, marked slow)
```

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Total Python Tests | 959 | 1130+ |
| Overall Coverage | ~44% | >60% |
| HTTP Server Coverage | 0% | >85% |
| DHT Bootstrap Coverage | 0% | >90% |
| curl/wget Coverage | 0% | >85% |
| listen Coverage | 0% | >85% |
| Network Tools Coverage | Limited | >75% |
| CLI Registration | Partial | 100% (25 commands) |
| WNS CLI Coverage | Partial | 100% (18 subcommands) |
| Smoke Tests | 0 | 8 |

---

## Notes

### Test File Creation Order (by dependency)

1. `tests/unit/test_http_server.py` - No dependencies
2. `tests/unit/test_dht_bootstrap.py` - No dependencies
3. `tests/unit/test_curl.py` - Uses http_client
4. `tests/unit/test_wget.py` - Uses http_client
5. `tests/unit/test_listen.py` - Uses http_server, forwarder
6. `tests/unit/test_cli_registration.py` - Uses main CLI
7. `tests/unit/test_ping.py` - Uses protocol
8. `tests/unit/test_tunnel.py` - Uses protocol
8. `tests/unit/test_proxy.py` - Uses protocol
9. `tests/unit/test_rsync.py` - Uses protocol
10. Functional tests (after unit tests pass)
11. Security/error tests
12. Smoke/performance tests

### Fixtures to Add to conftest.py

```python
@pytest.fixture
def mock_http_file_server(tmp_path):
    """Create test file structure for HTTP server tests."""
    (tmp_path / "index.html").write_text("<html>Hello</html>")
    (tmp_path / "style.css").write_text("body { color: black; }")
    (tmp_path / "script.js").write_text("console.log('test');")
    (tmp_path / "data.json").write_text('{"key": "value"}')
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "index.html").write_text("<html>Subdir</html>")
    return tmp_path

@pytest.fixture
def mock_click_context():
    """Create mock Click context for CLI tests."""
    ctx = MagicMock()
    ctx.obj = {
        'relay': 'ws://relay.example.com',
        'transit': None,
        'code_length': 2,
        'verbose': 0,
        'namespace': None,
    }
    return ctx
```

---

## Appendix: Test Template Examples

### Unit Test Template
```python
"""Unit tests for {module} module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class Test{ClassName}:
    """Tests for {ClassName} class."""

    def test_{method}_basic(self):
        """Test {method} with basic input."""
        # Arrange

        # Act

        # Assert
        pass

    @pytest.mark.asyncio
    async def test_{method}_async(self):
        """Test async {method}."""
        # Arrange

        # Act

        # Assert
        pass
```

### Functional Test Template
```python
"""Functional tests for {command} CLI command."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock


class Test{Command}CLI:
    """Functional tests for wh {command}."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_{command}_help(self, runner):
        """Test {command} --help output."""
        from wh.cli.{module} import {command}
        result = runner.invoke({command}, ['--help'])
        assert result.exit_code == 0
        assert '{expected_text}' in result.output.lower()
```
