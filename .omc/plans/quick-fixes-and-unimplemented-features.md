# Work Plan: Quick Fixes and Unimplemented Features

> **Generated**: 2026-01-23
> **Project**: Critical Wormhole Tools (CWT)
> **Current Version**: 0.4.0
> **Scope**: Quick fixes, Phase 5 completion, Phase 6 implementation, future roadmap items
> **Plan Version**: 2.0 (Revised per Critic/Architect feedback)

---

## Context

### Original Request
Complete all quick fixes and unimplemented features for Critical Wormhole Tools, including:
- Quick fixes for inconsistencies and missing files
- Browser extension publishing
- Caddy plugin real-world testing
- Phase 6 Enterprise Features (full implementation)
- Future roadmap items (mobile apps, native modules)

### Current State Analysis

**Completed Phases:**
- Phase 1: Core Tools (nc, ssh, scp, sftp, curl, wget)
- Phase 2: Additional Network Tools (ping, tunnel, proxy, rsync, telnet, ftp, nmap, traceroute, dns, mount, vnc, rdp)
- Phase 3: Wormhole Name Service (Ed25519 identities, DHT, aliases)
- Phase 4: Browser Extension (Chrome/Firefox MV3, 552 tests)

**In Progress:**
- Phase 5: Web Server Integration (Caddy plugin complete, needs testing)

**Not Started:**
- Phase 6: Enterprise Features
- Mobile Apps
- Native Nginx/Traefik modules

### Identified Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| FIXES.md missing | HIGH | No fix tracking file exists |
| Version mismatch | HIGH | pyproject.toml=0.4.0, manifest.json=0.5.0 |
| CHANGELOG date | MEDIUM | Placeholder `[0.1.0] - 2024-01-XX` |
| Test count inconsistency | LOW | Docs claim 827/745/1300 tests in different places |
| Privacy policy missing | HIGH | Required for Chrome Web Store |
| Extension not published | HIGH | Not in Chrome Web Store or Firefox Add-ons |
| Caddy plugin untested | MEDIUM | No real wormhole connection tests |
| ROADMAP.md Caddy status | LOW | Shows "Scaffold" but PLAN.md shows "Complete" - needs reconciliation |

---

## Work Objectives

### Core Objective
Bring Critical Wormhole Tools to production-ready state with all quick fixes resolved, browser extension published, and Phase 6 enterprise features fully implemented.

### Deliverables
1. FIXES.md tracking file created and maintained
2. All version inconsistencies resolved
3. Privacy policy document for browser extension
4. Browser extension published to Chrome Web Store and Firefox Add-ons
5. Caddy plugin tested with real wormhole connections
6. Phase 6 enterprise features fully implemented
7. Mobile app scaffolding (iOS/Android)
8. Native Nginx module scaffold
9. Native Traefik plugin scaffold
10. All documentation synchronized
11. All improvements actioned (implemented, not just documented)

### Definition of Done
- All tasks marked complete with passing tests
- FIXES.md documents every fix made
- All tests pass (Python + Browser Extension)
- Documentation updated and consistent
- Git commits AND PUSHES after each verified fix
- All improvements implemented (not deferred)

---

## Guardrails

### Must Have
- Testing pyramid enforcement: If bug found during testing, write failing unit/functional test FIRST, then fix, then verify test passes
- FIXES.md entry for every fix
- Commit AND PUSH after each verified fix (explicit in every task)
- Documentation sync after each change
- All fixes preserve backward compatibility
- Improvements must be IMPLEMENTED, not just documented

### Must NOT Have
- Breaking changes to existing APIs
- Time estimates in any deliverables
- Deferral language ("nice to have", "future consideration")
- Unverified fixes (all must have tests)
- Uncommitted/unpushed work at end of session
- Improvements documented without implementation

---

## Task Flow and Dependencies

```
[PHASE A: Quick Fixes]
    |
    v
[1. Create FIXES.md] --> [2. Fix Version Mismatch] --> [3. Fix CHANGELOG Date]
    |                           |
    v                           v
[4. Reconcile Test Counts] --> [5. Create Privacy Policy]
    |
    v
[PHASE B: Browser Extension Publishing]
    |
    v
[6. Chrome Web Store Prep] --> [6.5. Chrome Account Verification (USER GATE)]
    |                                   |
    v                                   v
[7. Submit to Chrome] --> [8. Firefox Add-ons Prep] --> [8.5. Firefox Account Verification (USER GATE)]
    |                                                            |
    v                                                            v
[9. Submit to Firefox] ------------------------------------------|
    |
    v
[PHASE C: Caddy Plugin Validation] (CAN RUN IN PARALLEL if Phase B blocked)
    |
    v
[10. Write Integration Tests] --> [11. Test with Real Wormhole] --> [12. Document Results]
    |
    v
[PHASE D: Phase 6 - Enterprise Features] (CAN RUN IN PARALLEL if Phase B blocked)
    |
    v
[13. Authentication Module] --> [14. Audit Logging] --> [15. Rate Limiting]
    |                                                            |
    v                                                            v
[16. Multi-Tenancy] --------------------------------------------|
    |
    v
[PHASE E: Future Roadmap] (CAN RUN IN PARALLEL if Phase B blocked)
    |
    v
[17. Mobile App Scaffold] --> [18. Native Nginx Module] --> [19. Native Traefik Plugin]
    |
    v
[PHASE F: Final Actions]
    |
    v
[20. Documentation Sync] --> [21. Test Suite Verification] --> [22. Improvement Iteration Loop]
                                                                    |
                                                                    v
                                                        [22a. Document Improvements]
                                                                    |
                                                                    v
                                                        [22b. Prioritize by Impact/Effort]
                                                                    |
                                                                    v
                                                        [22c. Implement High-Priority Improvements]
                                                                    |
                                                                    v
                                                        [22d. Re-run Test Suite]
                                                                    |
                                                                    v
                                                        [22e. Check for New Improvements]
                                                                    |
                                                                    v
                                                        (If new improvements found, goto 22a)
                                                        (Exit when no actionable improvements remain)
```

---

## Detailed Tasks

### PHASE A: Quick Fixes

#### Task 1: Create FIXES.md Tracking File
**Objective**: Establish fix tracking infrastructure per user requirements

**Pre-conditions**: None

**Acceptance Criteria**:
- [ ] FIXES.md created at repository root
- [ ] Template includes: Date, Issue, Root Cause, Fix Applied, Tests Added, Related Files
- [ ] First entry documents this file's creation
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/FIXES.md`

**Test Requirements**:
- N/A (documentation file)

**Documentation Updates**:
- Add FIXES.md to repository structure in PLAN.md

---

#### Task 2: Fix Version Mismatch
**Objective**: Synchronize version numbers across all files

**Pre-conditions**: Task 1 complete

**Issue**: pyproject.toml=0.4.0, browser-extension/manifest.json=0.5.0

**Research Required**:
- Determine correct version (0.4.0 per PLAN.md)
- Identify all files containing version numbers

**Acceptance Criteria**:
- [ ] All version numbers synchronized to 0.4.0
- [ ] Test written to verify version consistency
- [ ] FIXES.md entry added
- [ ] Changes committed and pushed to remote

**Files to Modify**:
- `/browser-extension/manifest.json` (change 0.5.0 to 0.4.0)
- `/browser-extension/package.json` (verify version)
- `/discovery-site/package.json` (verify version)

**Test Requirements**:
- Create `tests/unit/test_version_consistency.py` that reads all version files and asserts equality

**Documentation Updates**:
- FIXES.md entry
- CHANGELOG.md if needed

---

#### Task 3: Fix CHANGELOG Date Placeholder
**Objective**: Replace placeholder date with actual release date

**Pre-conditions**: Task 1 complete

**Issue**: `[0.1.0] - 2024-01-XX` contains placeholder

**Research Required**:
- Check git history for v0.1.0 tag date
- If no tag, use first commit date or reasonable estimate

**Acceptance Criteria**:
- [ ] Date placeholder replaced with actual date
- [ ] FIXES.md entry added
- [ ] Changes committed and pushed to remote

**Files to Modify**:
- `/CHANGELOG.md`

**Test Requirements**:
- N/A (manual verification)

**Documentation Updates**:
- FIXES.md entry

---

#### Task 4: Reconcile Test Count Documentation
**Objective**: Ensure consistent test counts across all documentation

**Pre-conditions**: Task 1 complete

**Issue**: Different documents claim different test counts (827, 745, 552, 1300)

**Research Required**:
- Run `pytest --collect-only` to get actual Python test count
- Run `npm test -- --reporter=json` to get actual browser test count
- Audit all documentation files for test count claims

**Acceptance Criteria**:
- [ ] Actual test counts determined
- [ ] All documentation updated with consistent, accurate counts
- [ ] FIXES.md entry added
- [ ] Changes committed and pushed to remote

**Files to Modify**:
- `/README.md`
- `/PLAN.md`
- `/browser-extension/README.md`
- Any other files with test count claims

**Test Requirements**:
- Add CI check script: `scripts/verify_test_counts.py` that:
  1. Runs `pytest --collect-only -q` and counts tests
  2. Runs `npm test -- --reporter=json` in browser-extension and counts tests
  3. Greps all .md files for test count claims
  4. Fails if documented counts differ from actual counts by more than 5%
- Add GitHub Actions step that runs this script on every PR

**Documentation Updates**:
- FIXES.md entry
- All affected documentation files

---

#### Task 5: Create Privacy Policy for Browser Extension
**Objective**: Create privacy policy required for Chrome Web Store

**Pre-conditions**: Task 1 complete

**Acceptance Criteria**:
- [ ] Privacy policy created explaining data handling
- [ ] Policy covers: data collected, data sharing, permissions used
- [ ] FIXES.md entry added
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/browser-extension/PRIVACY.md`
- `/docs/privacy-policy.md` (web-accessible version)

**Content Requirements**:
- What data the extension collects (connection codes, browsing to wh:// URLs)
- What data is stored locally (preferences, recent connections)
- What data is transmitted (to relay servers only, E2E encrypted)
- No personal data collection
- No analytics/tracking
- Permission justifications (proxy, storage, tabs, etc.)

**Test Requirements**:
- N/A (documentation file)

**Documentation Updates**:
- FIXES.md entry
- Browser extension README to reference privacy policy

---

### PHASE B: Browser Extension Publishing

#### Task 6: Chrome Web Store Preparation
**Objective**: Prepare all assets for Chrome Web Store submission

**Pre-conditions**: Tasks 1-5 complete

**Acceptance Criteria**:
- [ ] Store listing description written (max 132 chars for short, full for detailed)
- [ ] Screenshots captured (1280x800 or 640x400)
- [ ] Promotional images created (440x280 small, 920x680 large marquee)
- [ ] Icon variants verified (16, 32, 48, 128 px)
- [ ] Extension packaged as .zip
- [ ] Changes committed and pushed to remote

**Files to Create/Verify**:
- `/browser-extension/store-assets/`
  - `description-short.txt`
  - `description-full.txt`
  - `screenshots/` (at least 2)
  - `promo-small.png` (440x280)
  - `promo-large.png` (920x680)

**Pre-submission Checklist**:
- [ ] manifest.json permissions minimal and justified
- [ ] No external script loading (MV3 compliance)
- [ ] CSP properly configured
- [ ] Privacy policy URL ready

**Test Requirements**:
- Manual testing of packaged extension in clean Chrome profile

**Documentation Updates**:
- FIXES.md entry
- Browser extension README with store link placeholder

---

#### Task 6.5: Chrome Developer Account Verification (USER GATE)
**Objective**: Verify Chrome Web Store developer account exists and is accessible

**Pre-conditions**: Task 6 complete

**Type**: USER-GATED CHECKPOINT (Interactive)

**Acceptance Criteria**:
- [ ] User confirms Chrome Web Store Developer account exists
- [ ] User confirms ability to access Chrome Developer Dashboard
- [ ] If no account: User either creates one ($5 one-time fee) OR marks Phase B Chrome tasks as BLOCKED
- [ ] Verification documented in FIXES.md
- [ ] Changes committed and pushed to remote

**User Prompts**:
1. "Do you have a Chrome Web Store Developer account? (Y/N)"
2. If N: "Would you like to create one now? ($5 one-time fee at https://chrome.google.com/webstore/devconsole/register)"
3. If user declines: Mark Tasks 7 as BLOCKED, continue with Firefox track and Phases C, D, E

**Blocking Behavior**:
- If blocked: Phases C, D, E can proceed in parallel
- Document block reason in FIXES.md
- Add to ROADMAP.md as "Blocked: Awaiting Chrome Developer Account"

**Documentation Updates**:
- FIXES.md entry

---

#### Task 7: Submit to Chrome Web Store
**Objective**: Submit extension for Chrome Web Store review

**Pre-conditions**: Task 6 and 6.5 complete, developer account verified

**Acceptance Criteria**:
- [ ] Extension submitted to Chrome Web Store
- [ ] All required fields completed
- [ ] Privacy policy linked
- [ ] Submission confirmation received
- [ ] Submission status documented and pushed to remote

**Process**:
1. Navigate to Chrome Web Store Developer Dashboard
2. Create new item
3. Upload .zip package
4. Fill store listing (title, description, category)
5. Upload screenshots and promotional images
6. Set privacy policy URL
7. Submit for review

**Store Rejection Contingency**:
If extension is rejected:
1. Document rejection reason in FIXES.md
2. Address each rejection point as a sub-task (7a, 7b, etc.)
3. Each fix follows testing pyramid: write failing test if applicable, then fix
4. Re-submit and document new submission
5. Repeat until approved or escalate to user

**Documentation Updates**:
- FIXES.md entry
- Update PLAN.md with submission status
- Update browser-extension/README.md with store link

---

#### Task 8: Firefox Add-ons Preparation
**Objective**: Prepare assets for Firefox Add-ons submission

**Pre-conditions**: Task 6 complete (reuse assets where possible)

**Acceptance Criteria**:
- [ ] AMO listing description written
- [ ] Extension signed for distribution
- [ ] Source code archive prepared (AMO may request)
- [ ] Changes committed and pushed to remote

**Firefox-Specific Requirements**:
- Verify `browser_specific_settings.gecko` in manifest.json
- Test in Firefox Developer Edition
- Prepare source code if requested by reviewers

**Files to Verify**:
- `/browser-extension/manifest.json` (gecko settings)

**Test Requirements**:
- Manual testing in Firefox

**Documentation Updates**:
- FIXES.md entry

---

#### Task 8.5: Firefox Developer Account Verification (USER GATE)
**Objective**: Verify Firefox Add-ons developer account exists and is accessible

**Pre-conditions**: Task 8 complete

**Type**: USER-GATED CHECKPOINT (Interactive)

**Acceptance Criteria**:
- [ ] User confirms addons.mozilla.org (AMO) developer account exists
- [ ] User confirms ability to access AMO Developer Hub
- [ ] If no account: User either creates one (free) OR marks Phase B Firefox tasks as BLOCKED
- [ ] Verification documented in FIXES.md
- [ ] Changes committed and pushed to remote

**User Prompts**:
1. "Do you have a Firefox Add-ons (AMO) developer account? (Y/N)"
2. If N: "Would you like to create one now? (Free at https://addons.mozilla.org/developers/)"
3. If user declines: Mark Task 9 as BLOCKED, continue with Phases C, D, E

**Blocking Behavior**:
- If blocked: Phases C, D, E can proceed in parallel
- Document block reason in FIXES.md
- Add to ROADMAP.md as "Blocked: Awaiting Firefox Developer Account"

**Documentation Updates**:
- FIXES.md entry

---

#### Task 9: Submit to Firefox Add-ons
**Objective**: Submit extension for Firefox Add-ons review

**Pre-conditions**: Task 8 and 8.5 complete, AMO account verified

**Acceptance Criteria**:
- [ ] Extension submitted to addons.mozilla.org
- [ ] All required fields completed
- [ ] Submission confirmation received
- [ ] Submission status documented and pushed to remote

**Process**:
1. Navigate to AMO Developer Hub
2. Submit new add-on
3. Upload .zip package
4. Fill listing details
5. Submit for review

**Store Rejection Contingency**:
If extension is rejected:
1. Document rejection reason in FIXES.md
2. Address each rejection point as a sub-task (9a, 9b, etc.)
3. Each fix follows testing pyramid: write failing test if applicable, then fix
4. Re-submit and document new submission
5. Repeat until approved or escalate to user

**Documentation Updates**:
- FIXES.md entry
- Update PLAN.md with submission status
- Update browser-extension/README.md with AMO link

---

### PHASE C: Caddy Plugin Validation

> **Note**: This phase can run in parallel with Phases D and E if Phase B is blocked on developer accounts.

#### Task 10: Write Caddy Integration Tests
**Objective**: Create tests that verify Caddy plugin with mocked wormhole connections

**Pre-conditions**: None

**Acceptance Criteria**:
- [ ] Integration tests for Caddy listener
- [ ] Tests cover: connection acceptance, HTTP forwarding, connection close
- [ ] Tests use mock daemon responses
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/integrations/caddy/integration_test.go`

**Test Requirements**:
- Mock HTTP server for daemon API
- Test WormholeListener accepts connections
- Test WormholeConn Read/Write
- Test deadline handling

**Documentation Updates**:
- FIXES.md entry
- Caddy README with test instructions

**Note**: Reconcile ROADMAP.md Caddy status (shows "Scaffold") with PLAN.md (shows "Complete") during this task. Update both to reflect actual state after testing.

---

#### Task 11: Test Caddy Plugin with Real Wormhole
**Objective**: Validate Caddy plugin works with actual wormhole connections

**Pre-conditions**: Task 10 complete

**Acceptance Criteria**:
- [ ] Manual test: Caddy serves content over wormhole
- [ ] Manual test: Browser extension can connect to Caddy site
- [ ] Performance baseline established
- [ ] Any issues fixed following testing pyramid methodology (see below)
- [ ] Changes committed and pushed to remote

**Testing Pyramid Enforcement for Bug Fixes**:
If any bug is discovered during testing:
1. **FIRST**: Write a unit test or functional test that reproduces the bug (test should FAIL)
2. **SECOND**: Implement the fix
3. **THIRD**: Verify the test now PASSES
4. **FOURTH**: Run full test suite to ensure no regressions
5. Document in FIXES.md with reference to the new test

**Test Procedure**:
1. Start `wh daemon start`
2. Configure Caddy with wormhole listener
3. Start Caddy: `caddy run`
4. Note wormhole code from output
5. Test with `wh curl wh://[code]/`
6. Test with browser extension

**Files to Modify**:
- `/integrations/caddy/` (any bug fixes)

**Documentation Updates**:
- FIXES.md for any bugs found (with test references)
- Caddy README with real-world test results

---

#### Task 12: Document Caddy Integration Results
**Objective**: Complete documentation for Caddy plugin

**Pre-conditions**: Task 11 complete

**Acceptance Criteria**:
- [ ] Caddy README includes working examples
- [ ] Known limitations documented
- [ ] Troubleshooting section added
- [ ] Changes committed and pushed to remote

**Files to Modify**:
- `/integrations/caddy/README.md`

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Caddy status to Complete - reconcile with current "Scaffold" status)
- PLAN.md (update Phase 5 status)

---

### PHASE D: Phase 6 - Enterprise Features

> **Note**: This phase can run in parallel with Phases C and E if Phase B is blocked on developer accounts.

#### Task 13: Authentication & Authorization Module
**Objective**: Implement LDAP/AD integration for wormhole authentication

**Pre-conditions**: None

**Acceptance Criteria**:
- [ ] `--auth-method` flag added to `wh listen`
- [ ] Supported methods: `none`, `pubkey`, `password`, `ldap`
- [ ] LDAP configuration via `--ldap-server`, `--ldap-base-dn`
- [ ] Authorized keys file support
- [ ] Unit tests for auth module
- [ ] Integration tests with mock LDAP
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/src/wh/enterprise/__init__.py`
- `/src/wh/enterprise/auth.py`
- `/src/wh/enterprise/ldap_client.py`
- `/tests/unit/test_enterprise_auth.py`

**Files to Modify**:
- `/src/wh/cli/listen.py` (add auth flags)
- `/pyproject.toml` (add ldap3 dependency)

**CLI Interface**:
```bash
# Public key authentication
wh listen --ssh --auth-method=pubkey --authorized-keys=/etc/wh/authorized_keys

# LDAP authentication
wh listen --ssh --auth-method=ldap --ldap-server=ldap://ad.company.com --ldap-base-dn="dc=company,dc=com"

# Password authentication (existing)
wh listen --ssh --auth-method=password
```

**Test Requirements**:
- Unit tests for auth module
- Mock LDAP server tests
- Integration test with actual LDAP (optional, CI skip)

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Phase 6 Auth status)
- README.md (Enterprise Features section)
- Create `/docs/enterprise/authentication.md`

---

#### Task 14: Audit Logging Module
**Objective**: Implement structured audit logging for SIEM integration

**Pre-conditions**: Task 13 complete (auth events need logging)

**Acceptance Criteria**:
- [ ] `--audit-log` flag for daemon and listen commands
- [ ] JSON log format with timestamp, event, code, peer, action
- [ ] Log rotation support
- [ ] Unit tests for logging module
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/src/wh/enterprise/audit.py`
- `/tests/unit/test_enterprise_audit.py`

**Files to Modify**:
- `/src/wh/cli/daemon.py` (add --audit-log flag)
- `/src/wh/cli/listen.py` (add --audit-log flag)
- `/src/wh/core/wormhole_manager.py` (emit audit events)

**Log Format**:
```json
{
  "timestamp": "2026-01-23T10:15:30.123Z",
  "event": "connection",
  "code": "7-guitar-sunset",
  "peer": "a7b3c9d2e1f4",
  "action": "ssh",
  "user": "admin",
  "source_ip": "192.168.1.100",
  "duration_ms": 45230,
  "bytes_sent": 12345,
  "bytes_recv": 67890
}
```

**Events to Log**:
- `connection_start` - New wormhole connection
- `connection_end` - Connection closed
- `auth_success` - Authentication succeeded
- `auth_failure` - Authentication failed
- `file_transfer` - File sent/received
- `command_exec` - Command executed (SSH)

**Test Requirements**:
- Unit tests for log formatting
- Unit tests for log rotation
- Integration test for log file creation

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Phase 6 Audit status)
- Create `/docs/enterprise/audit-logging.md`

---

#### Task 15: Rate Limiting & Quotas Module
**Objective**: Implement connection rate limiting and bandwidth quotas

**Pre-conditions**: Task 14 complete (need audit for quota tracking)

**Acceptance Criteria**:
- [ ] Policy file format defined (YAML)
- [ ] `--policy` flag for daemon
- [ ] Rate limiting by IP, identity, global
- [ ] Bandwidth quotas (bytes/day)
- [ ] Concurrent connection limits
- [ ] Unit tests for rate limiter
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/src/wh/enterprise/policy.py`
- `/src/wh/enterprise/rate_limiter.py`
- `/tests/unit/test_enterprise_policy.py`
- `/tests/unit/test_enterprise_rate_limiter.py`

**Files to Modify**:
- `/src/wh/cli/daemon.py` (add --policy flag)
- `/src/wh/core/wormhole_manager.py` (enforce limits)

**Policy File Format**:
```yaml
# /etc/wh/policy.yml
rate_limits:
  connections_per_minute: 10
  connections_per_minute_per_ip: 5
  bandwidth_mbps: 100

quotas:
  max_concurrent_connections: 50
  max_transfer_gb_per_day: 100
  max_session_duration_minutes: 480

exceptions:
  - identity: "a7b3c9d2e1f4"
    unlimited: true
  - ip_range: "10.0.0.0/8"
    connections_per_minute: 100
```

**Test Requirements**:
- Unit tests for policy parsing
- Unit tests for rate limiter logic
- Integration tests for quota enforcement

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Phase 6 Rate Limiting status)
- Create `/docs/enterprise/rate-limiting.md`

---

#### Task 16: Multi-Tenancy Module
**Objective**: Implement namespace isolation for teams

**Pre-conditions**: Tasks 13-15 complete

**Acceptance Criteria**:
- [ ] `--namespace` flag for all commands
- [ ] Namespace isolation (same codes don't conflict)
- [ ] Namespace-specific DHT prefix
- [ ] Admin commands for namespace management
- [ ] Unit tests for namespace module
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/src/wh/enterprise/namespace.py`
- `/tests/unit/test_enterprise_namespace.py`

**Files to Modify**:
- `/src/wh/cli/main.py` (add --namespace global option)
- `/src/wh/wns/dht.py` (namespace-scoped DHT operations)
- `/src/wh/core/wormhole_manager.py` (namespace in code prefix)

**CLI Interface**:
```bash
# All commands support --namespace
wh --namespace=engineering listen --ssh
wh --namespace=engineering ssh 7-guitar-sunset
wh --namespace=sales nc -l

# Namespace admin commands
wh namespace create engineering --admin=admin@company.com
wh namespace list
wh namespace delete engineering --force
```

**Test Requirements**:
- Unit tests for namespace isolation
- Unit tests for DHT prefix generation
- Integration tests for cross-namespace isolation

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Phase 6 Multi-Tenancy status)
- Create `/docs/enterprise/multi-tenancy.md`
- Update PLAN.md (Phase 6 complete)

---

### PHASE E: Future Roadmap

> **Note**: This phase can run in parallel with Phases C and D if Phase B is blocked on developer accounts.

#### Task 17: Mobile App Scaffold (iOS + Android)
**Objective**: Create project scaffolding for native mobile apps

**Pre-conditions**: None (can run in parallel with Phase D)

**Acceptance Criteria**:
- [ ] React Native project initialized
- [ ] Shared protocol library planned
- [ ] Basic app structure with screens
- [ ] Build instructions documented
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/mobile/README.md`
- `/mobile/package.json`
- `/mobile/app.json`
- `/mobile/src/` (basic structure)
- `/mobile/ios/` (generated)
- `/mobile/android/` (generated)

**App Screens**:
- Home (connect by code)
- WNS Browser (enter wh:// URLs)
- Identities (manage WNS identities)
- Settings (relay config, preferences)

**Test Requirements**:
- Basic Jest setup for React Native
- Placeholder tests for core functionality

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Mobile Apps status to "In Progress")
- Create `/mobile/README.md`

---

#### Task 18: Native Nginx Module Scaffold
**Objective**: Create scaffold for native nginx wormhole module

**Pre-conditions**: None

**Acceptance Criteria**:
- [ ] C module scaffold created
- [ ] Build system (CMake or autoconf)
- [ ] README with architecture plan
- [ ] Basic request handling stub
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/integrations/nginx-native/README.md`
- `/integrations/nginx-native/CMakeLists.txt`
- `/integrations/nginx-native/ngx_http_wormhole_module.c`
- `/integrations/nginx-native/config`

**Module Architecture**:
```c
// ngx_http_wormhole_module.c
// - wormhole_enable directive
// - wormhole_name directive
// - wormhole_key directive
// - Handler that connects to wh daemon
```

**Test Requirements**:
- Build test (compiles successfully)
- Basic nginx config test

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Nginx Module status)
- Update integrations/README.md

---

#### Task 19: Native Traefik Plugin Scaffold
**Objective**: Create scaffold for native Traefik wormhole plugin

**Pre-conditions**: None

**Acceptance Criteria**:
- [ ] Go plugin scaffold created
- [ ] Traefik plugin manifest
- [ ] README with architecture plan
- [ ] Basic middleware stub
- [ ] Changes committed and pushed to remote

**Files to Create**:
- `/integrations/traefik-native/README.md`
- `/integrations/traefik-native/go.mod`
- `/integrations/traefik-native/wormhole.go`
- `/integrations/traefik-native/.traefik.yml`

**Plugin Architecture**:
```go
// wormhole.go
// - WormholeMiddleware struct
// - ServeHTTP that routes wh:// requests
// - Configuration for identity/naming
```

**Test Requirements**:
- Build test (compiles successfully)
- Basic Traefik config test

**Documentation Updates**:
- FIXES.md entry
- ROADMAP.md (update Traefik Plugin status)
- Update integrations/README.md

---

### PHASE F: Final Actions

#### Task 20: Documentation Synchronization
**Objective**: Ensure all documentation is consistent and up-to-date

**Pre-conditions**: Tasks 1-19 complete

**Acceptance Criteria**:
- [ ] All README.md files reviewed and updated
- [ ] PLAN.md reflects current state
- [ ] ROADMAP.md reflects current state
- [ ] CHANGELOG.md has all changes
- [ ] Version numbers consistent everywhere
- [ ] All documentation patterns checked (see expanded list below)
- [ ] Changes committed and pushed to remote

**Files to Review** (EXPANDED per user requirements):
- `/README.md`
- `/PLAN.md`
- `/ROADMAP.md`
- `/CHANGELOG.md`
- `/SECURITY.md`
- `/CONTRIBUTING.md`
- `/FIXES.md`
- `/browser-extension/README.md`
- `/discovery-site/README.md`
- `/integrations/*/README.md`
- `/docs/*.md`
- `/mobile/README.md` (if created)

**Additional Documentation Patterns to Check** (if they exist):
- `*SESSION*.md` - Session tracking files
- `*PHASE*.md` - Phase documentation files
- `*COMPLETE*.md` - Completion documentation
- `*STATUS*.md` - Status tracking files
- `*TEST*.md` - Test documentation files
- `*DEPLOY*.md` - Deployment documentation
- `*ROLLOUT*.md` - Rollout documentation

**Documentation Updates**:
- FIXES.md entry
- All files listed above as needed

---

#### Task 21: Test Suite Verification
**Objective**: Verify all tests pass and coverage is acceptable

**Pre-conditions**: Task 20 complete

**Acceptance Criteria**:
- [ ] All Python tests pass: `pytest`
- [ ] All browser tests pass: `npm test`
- [ ] Coverage report generated
- [ ] No regressions from fixes
- [ ] Changes committed and pushed to remote

**Testing Pyramid Enforcement**:
If any test fails:
1. **DO NOT** simply fix the failing test
2. **ANALYZE** why the test is failing
3. If it's a legitimate bug discovered: follow testing pyramid (Task 11 methodology)
4. If it's a test issue: fix the test, document reasoning

**Commands to Run**:
```bash
# Python tests
pytest --cov=wh --cov-report=html

# Browser extension tests
cd browser-extension && npm test

# Linting
ruff check src tests
cd browser-extension && npm run lint
```

**Documentation Updates**:
- FIXES.md entry with final test counts

---

#### Task 22: Improvement Iteration Loop
**Objective**: Implement all improvements discovered during work (NOT just document them)

**Pre-conditions**: Task 21 complete

**CRITICAL**: Per user requirement #7, improvements must be ACTIONED (implemented), not just documented. This task is an iteration loop that continues until no actionable improvements remain.

---

##### Task 22a: Document Improvements
**Objective**: Catalog all improvements discovered during Tasks 1-21

**Acceptance Criteria**:
- [ ] Review FIXES.md for improvement opportunities noted during fixes
- [ ] Review test output for suggested improvements
- [ ] Review documentation for inconsistencies or gaps
- [ ] All improvements documented in `/IMPROVEMENTS.md`
- [ ] Changes committed and pushed to remote

**Improvement Template**:
```markdown
### Improvement: [Title]
**Discovered During**: Task [N]
**Category**: [Bug | Enhancement | Refactor | Documentation | Performance | Test Coverage]
**Impact**: [High | Medium | Low] - How much this improves the project
**Effort**: [High | Medium | Low] - How much work to implement
**Description**: [What could be improved]
**Implementation**: [Specific steps to implement]
**Actionable**: [Yes | No] - Can this be implemented now?
```

---

##### Task 22b: Prioritize by Impact/Effort
**Objective**: Rank improvements for implementation order

**Acceptance Criteria**:
- [ ] Each improvement scored by Impact and Effort
- [ ] High Impact / Low Effort items prioritized first
- [ ] Priority list added to IMPROVEMENTS.md
- [ ] Changes committed and pushed to remote

**Prioritization Matrix**:
| Impact \ Effort | Low Effort | Medium Effort | High Effort |
|-----------------|------------|---------------|-------------|
| High Impact     | P1 - Do First | P2 - Do Second | P3 - Do Third |
| Medium Impact   | P2 - Do Second | P3 - Do Third | P4 - Consider |
| Low Impact      | P3 - Do Third | P4 - Consider | P5 - Defer* |

*P5 items may be deferred ONLY if not actionable (e.g., requires external dependency)

---

##### Task 22c: Implement High-Priority Improvements
**Objective**: Implement all P1, P2, and P3 improvements

**Acceptance Criteria**:
- [ ] All P1 improvements implemented
- [ ] All P2 improvements implemented
- [ ] All P3 improvements implemented
- [ ] Each improvement follows testing pyramid (if applicable)
- [ ] FIXES.md updated for each improvement
- [ ] Changes committed and pushed to remote after each improvement

**Testing Pyramid Enforcement**:
For each improvement that touches code:
1. Write failing test that validates the improvement is needed
2. Implement the improvement
3. Verify test passes
4. Run full test suite

**Exit Criteria for P4/P5**:
- P4 items: Implement unless blocked by external factors
- P5 items: Document in ROADMAP.md for future work ONLY if genuinely not actionable

---

##### Task 22d: Re-run Test Suite
**Objective**: Verify all improvements pass tests

**Acceptance Criteria**:
- [ ] All Python tests pass: `pytest`
- [ ] All browser tests pass: `npm test`
- [ ] No regressions introduced by improvements
- [ ] Coverage maintained or improved
- [ ] Changes committed and pushed to remote

---

##### Task 22e: Check for New Improvements
**Objective**: Determine if improvement implementations revealed new improvements

**Acceptance Criteria**:
- [ ] Review 22c implementations for secondary improvements
- [ ] Review test results for new issues
- [ ] Document any new improvements found

**Loop Decision**:
- If NEW actionable improvements found: **Return to Task 22a**
- If NO new actionable improvements: **Exit loop, proceed to completion**

**Exit Condition**: Loop terminates when:
1. No new actionable improvements are discovered, AND
2. All previously identified P1-P4 improvements are implemented

---

## Commit Strategy

Each task MUST result in a commit AND PUSH following this pattern:

```
[type](scope): brief description

- Detailed change 1
- Detailed change 2

FIXES.md: Added entry for [issue]
Tests: [test count] added/modified

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Commit Types**:
- `fix`: Bug fixes
- `feat`: New features
- `docs`: Documentation only
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

**Examples**:
- `fix(version): synchronize version to 0.4.0 across all files`
- `feat(auth): add LDAP authentication support`
- `docs(privacy): add privacy policy for browser extension`
- `test(caddy): add integration tests for wormhole listener`

**CRITICAL**: Every task acceptance criteria includes "committed and pushed to remote". No task is complete until changes are pushed.

---

## Success Criteria

### Phase Completion Checklist

**Phase A: Quick Fixes**
- [ ] FIXES.md exists and tracking all fixes
- [ ] Version mismatch resolved (0.4.0 everywhere)
- [ ] CHANGELOG date placeholder fixed
- [ ] Test counts consistent in docs
- [ ] Privacy policy created
- [ ] All changes committed and pushed

**Phase B: Browser Extension Publishing**
- [ ] Chrome Web Store submission complete (or documented as BLOCKED with reason)
- [ ] Firefox Add-ons submission complete (or documented as BLOCKED with reason)
- [ ] Store links added to documentation (where applicable)
- [ ] Store rejection contingencies documented if applicable
- [ ] All changes committed and pushed

**Phase C: Caddy Plugin Validation**
- [ ] Integration tests written and passing
- [ ] Real-world testing completed
- [ ] Documentation updated with results
- [ ] ROADMAP.md Caddy status reconciled
- [ ] All changes committed and pushed

**Phase D: Phase 6 Enterprise Features**
- [ ] Authentication module complete with tests
- [ ] Audit logging module complete with tests
- [ ] Rate limiting module complete with tests
- [ ] Multi-tenancy module complete with tests
- [ ] All changes committed and pushed

**Phase E: Future Roadmap**
- [ ] Mobile app scaffold created
- [ ] Native Nginx module scaffold created
- [ ] Native Traefik plugin scaffold created
- [ ] All changes committed and pushed

**Phase F: Final Actions**
- [ ] All documentation synchronized (including extended patterns)
- [ ] All tests passing
- [ ] Improvements IMPLEMENTED (not just documented)
- [ ] Improvement iteration loop completed (no actionable items remaining)
- [ ] All changes committed and pushed

### Overall Success Metrics
- Zero failing tests
- FIXES.md documents all changes
- All commits pushed to remote
- Documentation consistent
- No deferred work (except genuinely non-actionable items)
- All improvements actioned

---

## Risk Mitigation

### Browser Store Rejection
**Risk**: Extension rejected by Chrome/Firefox review
**Mitigation**:
- Review store policies before submission
- Minimize permissions
- Provide detailed privacy policy
- Respond promptly to reviewer feedback
**Contingency**: If rejected:
1. Document rejection reason in FIXES.md
2. Create sub-tasks (7a/9a, 7b/9b, etc.) to address each point
3. Re-submit and iterate until approved
4. If fundamentally blocked, escalate to user with options

### Developer Account Unavailability
**Risk**: User lacks Chrome/Firefox developer accounts
**Mitigation**:
- Tasks 6.5 and 8.5 are explicit user-gated checkpoints
- If blocked, Phases C, D, E can proceed in parallel
- Document block status in ROADMAP.md
- Return to browser publishing when accounts available

### LDAP Integration Complexity
**Risk**: LDAP integration more complex than expected
**Mitigation**:
- Start with mock LDAP in tests
- Support fallback to simpler auth methods
- Document known LDAP server compatibility

### Mobile App Scope Creep
**Risk**: Mobile scaffold expands beyond scaffold
**Mitigation**:
- Strictly limit to scaffold only
- Defer protocol implementation to future work
- Document scope clearly in mobile/README.md

### Improvement Loop Infinite Recursion
**Risk**: Task 22 loop never terminates
**Mitigation**:
- Clear exit condition: no NEW actionable improvements
- P5 items explicitly allowed to defer if genuinely blocked
- Maximum iteration count of 5 (if reached, escalate to user)

---

## Next Steps After Plan Completion

Run `/start-work` to begin execution of this plan.

The executor should:
1. Execute tasks in order (respect dependencies)
2. Run tests after each fix
3. If bug found: write failing test FIRST, then fix (testing pyramid)
4. Update FIXES.md after each fix
5. Commit AND PUSH after each verified fix
6. Update documentation as specified
7. Report any blockers immediately
8. For user-gated tasks (6.5, 8.5): pause and wait for user input
9. Complete Task 22 iteration loop until no improvements remain

---

*Plan generated by Prometheus (Claude Opus 4.5)*
*Plan version: 2.0 (Revised per Critic/Architect feedback)*
*Revision notes: Added commit/push to all tasks, testing pyramid enforcement, Task 22 iteration loop, Tasks 6.5/8.5 user gates, expanded Task 20 documentation patterns, store rejection contingencies, ROADMAP.md Caddy reconciliation note*
