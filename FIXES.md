# Fixes Log

This document tracks all fixes applied to Critical Wormhole Tools, including root cause analysis, tests added, and related files. This helps identify systemic problems and prevent regressions.

## Format

Each fix entry follows this template:

```markdown
### FIX-XXX: [Brief Title]
**Date**: YYYY-MM-DD
**Issue**: Description of the problem
**Root Cause**: Why the problem occurred
**Fix Applied**: What was changed
**Tests Added**: New tests to prevent regression
**Related Files**: List of modified files
**Systemic Notes**: Any patterns or related issues identified
```

---

## Fixes

### FIX-001: Create FIXES.md tracking file
**Date**: 2026-01-23
**Issue**: No fix tracking infrastructure existed in the project
**Root Cause**: Oversight during initial project setup
**Fix Applied**: Created FIXES.md with template for tracking all fixes
**Tests Added**: N/A (documentation file)
**Related Files**:
- `/FIXES.md` (this file)
- `/PLAN.md` (added FIXES.md to project structure)
**Systemic Notes**: Part of Phase A quick fixes to establish proper fix tracking per project requirements

---

### FIX-005: Missing privacy policy for browser extension
**Date**: 2026-01-23
**Issue**: No privacy policy existed, which is required for Chrome Web Store submission
**Root Cause**: Not created during initial browser extension development
**Fix Applied**:
- Created `/browser-extension/PRIVACY.md` with detailed privacy policy
- Created `/docs/privacy-policy.md` as web-accessible version
**Tests Added**: N/A (documentation files)
**Related Files**:
- `/browser-extension/PRIVACY.md`
- `/docs/privacy-policy.md`
**Systemic Notes**: Privacy policy should be created as part of any browser extension development

---

### FIX-004: Test count documentation inconsistency
**Date**: 2026-01-23
**Issue**: PLAN.md documented 745 Python tests but actual count is 791
**Root Cause**: Documentation not updated after adding new tests
**Fix Applied**:
- Updated PLAN.md Python test count from 745 to 791
- Created `scripts/verify_test_counts.py` to verify counts match
**Tests Added**: `scripts/verify_test_counts.py` (CI verification script)
**Related Files**:
- `/PLAN.md`
- `/scripts/verify_test_counts.py`
**Systemic Notes**: Test counts should be updated automatically in CI or during release process

---

### FIX-003: CHANGELOG date placeholder
**Date**: 2026-01-23
**Issue**: CHANGELOG.md had placeholder date `[0.1.0] - 2024-01-XX`
**Root Cause**: Date was left as placeholder during initial release
**Fix Applied**: Changed to `[0.1.0] - 2026-01-07` based on git history (first commit date)
**Tests Added**: N/A (documentation file)
**Related Files**:
- `/CHANGELOG.md`
**Systemic Notes**: Release dates should be set during the release process, not left as placeholders

---

### FIX-002: Version mismatch across project files
**Date**: 2026-01-23
**Issue**: Version numbers were inconsistent: pyproject.toml=0.4.0, manifest.json=0.5.0, discovery-site/package.json=0.5.0
**Root Cause**: Version bumps in JavaScript packages not synchronized with Python package
**Fix Applied**:
- Updated browser-extension/manifest.json from 0.5.0 to 0.4.0
- Updated discovery-site/package.json from 0.5.0 to 0.4.0
**Tests Added**: `tests/unit/test_version_consistency.py` - verifies all version files match
**Related Files**:
- `/browser-extension/manifest.json`
- `/discovery-site/package.json`
- `/tests/unit/test_version_consistency.py`
**Systemic Notes**: Version synchronization should be part of release process. Consider adding pre-commit hook to verify versions match.

---

### FIX-007: Browser extension store assets preparation
**Date**: 2026-01-23
**Issue**: Browser extension ready for publishing but store assets not prepared
**Root Cause**: Assets needed for Chrome Web Store and Firefox Add-ons submission
**Fix Applied**:
- Created `/browser-extension/store-assets/` directory
- Created `description-short.txt` (132 chars for Chrome)
- Created `description-full.txt` (detailed store listing)
- Created `README.md` with submission checklist
**Tests Added**: N/A (documentation files)
**Related Files**:
- `/browser-extension/store-assets/description-short.txt`
- `/browser-extension/store-assets/description-full.txt`
- `/browser-extension/store-assets/README.md`
**Systemic Notes**: Store submission BLOCKED - user opted to skip Chrome and Firefox publishing for now. Developer accounts not available.

---

### FIX-006: Caddy plugin integration tests and documentation
**Date**: 2026-01-23
**Issue**: Caddy plugin lacked integration tests and comprehensive documentation
**Root Cause**: Initial scaffold implementation focused on structure, not testing or examples
**Fix Applied**:
- Created `/integrations/caddy/integration_test.go` with 10 comprehensive integration tests
- Updated `/integrations/caddy/README.md` with:
  - Test instructions and coverage table
  - 3 working examples (static files, reverse proxy, multiple sites)
  - 5 documented known limitations with workarounds
  - Comprehensive troubleshooting section
  - Performance benchmarks and optimization tips
**Tests Added**:
- `TestIntegration_MockDaemonServer` - Daemon client with mock server
- `TestIntegration_WormholeListener` - Listener accepts connections
- `TestIntegration_WormholeConn_ReadWrite` - Read/write operations
- `TestIntegration_WormholeConn_PartialRead` - Buffering partial reads
- `TestIntegration_Deadline_Read` - Read deadline handling
- `TestIntegration_Deadline_Write` - Write deadline handling
- `TestIntegration_Deadline_Both` - SetDeadline for both read/write
- `TestIntegration_Connection_Lifecycle` - Full connection lifecycle
- `TestIntegration_MultipleConnections` - Concurrent connections
**Related Files**:
- `/integrations/caddy/integration_test.go`
- `/integrations/caddy/README.md`
- `/ROADMAP.md` (updated Caddy status from Scaffold to Complete)
**Systemic Notes**: Integration tests use mock HTTP servers to avoid dependency on running daemon, enabling reliable CI testing

---

### FIX-008: Future roadmap scaffolds created
**Date**: 2026-01-23
**Issue**: No scaffolding existed for future roadmap items (mobile app, native modules)
**Root Cause**: Phase E scaffolding planned but not yet implemented
**Fix Applied**:
- Created `/mobile/` directory with React Native app scaffold
  - package.json, app.json, README.md
  - 4 screens: HomeScreen, BrowserScreen, IdentitiesScreen, SettingsScreen
  - App.js with navigation setup
  - Basic Jest test structure
- Created `/integrations/nginx-native/` directory with native Nginx module scaffold
  - README.md with architecture and configuration documentation
  - CMakeLists.txt for build configuration
  - config file for Nginx module integration
  - ngx_http_wormhole_module.c with module skeleton and directives
- Created `/integrations/traefik-native/` directory with Traefik plugin scaffold
  - README.md with plugin documentation and examples
  - go.mod with dependencies
  - wormhole.go with middleware implementation stub
  - .traefik.yml plugin manifest
**Tests Added**:
- `/mobile/__tests__/App.test.js` - Basic smoke test
**Related Files**:
- `/mobile/` - Complete mobile app scaffold
- `/integrations/nginx-native/` - Nginx module scaffold
- `/integrations/traefik-native/` - Traefik plugin scaffold
- `/integrations/README.md` - Updated with new native modules
- `/ROADMAP.md` - Added Phase 6 for mobile and future features, marked Phase 5 complete
**Systemic Notes**: Scaffolds provide clear architecture and structure for future development. Mobile app uses React Native for cross-platform support. Native modules enable zero-dependency integration for advanced users.

---

### FIX-009: Add enterprise authentication module
**Date**: 2026-01-23
**Issue**: No authentication support for enterprise deployments
**Root Cause**: Phase 6 enterprise features not yet implemented
**Fix Applied**:
- Created `/src/wh/enterprise/__init__.py` - Enterprise module package
- Created `/src/wh/enterprise/auth.py` - Authentication with pubkey, password, LDAP support
- Created `/src/wh/enterprise/ldap_client.py` - LDAP connection pooling and utilities
- Updated `/src/wh/cli/listen.py` - Added --auth-method, --authorized-keys, --ldap-* flags
**Tests Added**: `/tests/unit/test_enterprise_auth.py` (20+ tests)
**Related Files**:
- `/src/wh/enterprise/__init__.py`
- `/src/wh/enterprise/auth.py`
- `/src/wh/enterprise/ldap_client.py`
- `/src/wh/cli/listen.py`
- `/tests/unit/test_enterprise_auth.py`
- `/docs/enterprise/authentication.md`
**Systemic Notes**: Part of Phase 6 enterprise features. LDAP requires ldap3 optional dependency.

---

### FIX-010: Add enterprise audit logging module
**Date**: 2026-01-23
**Issue**: No audit logging for compliance and security monitoring
**Root Cause**: Phase 6 enterprise features not yet implemented
**Fix Applied**:
- Created `/src/wh/enterprise/audit.py` - JSON audit logging with rotation support
- Updated `/src/wh/cli/listen.py` - Added --audit-log flag
**Tests Added**: `/tests/unit/test_enterprise_audit.py` (25+ tests)
**Related Files**:
- `/src/wh/enterprise/audit.py`
- `/src/wh/cli/listen.py`
- `/tests/unit/test_enterprise_audit.py`
- `/docs/enterprise/audit-logging.md`
**Systemic Notes**: Supports SIEM integration (Splunk, ELK, Datadog). Log format is one JSON object per line.

---

### FIX-011: Add enterprise rate limiting module
**Date**: 2026-01-23
**Issue**: No rate limiting or quota enforcement for enterprise deployments
**Root Cause**: Phase 6 enterprise features not yet implemented
**Fix Applied**:
- Created `/src/wh/enterprise/policy.py` - YAML policy file parsing with rule matching
- Created `/src/wh/enterprise/rate_limiter.py` - Token bucket rate limiting, quotas, bandwidth throttling
**Tests Added**:
- `/tests/unit/test_enterprise_policy.py` (30+ tests)
- `/tests/unit/test_enterprise_rate_limiter.py` (15+ tests)
**Related Files**:
- `/src/wh/enterprise/policy.py`
- `/src/wh/enterprise/rate_limiter.py`
- `/tests/unit/test_enterprise_policy.py`
- `/tests/unit/test_enterprise_rate_limiter.py`
- `/docs/enterprise/rate-limiting.md`
**Systemic Notes**: Supports per-IP, per-identity, and global limits with CIDR matching and wildcards.

---

### FIX-012: Add enterprise multi-tenancy namespace module
**Date**: 2026-01-23
**Issue**: No namespace isolation for multi-tenant deployments
**Root Cause**: Phase 6 enterprise features not yet implemented
**Fix Applied**:
- Created `/src/wh/enterprise/namespace.py` - Namespace management with DHT prefix isolation
- Created `/src/wh/cli/namespace.py` - CLI commands for namespace management
- Updated `/src/wh/cli/main.py` - Added --namespace global flag and namespace command group
- Updated `/src/wh/wns/dht.py` - Added namespace-prefixed DHT key support
**Tests Added**: `/tests/unit/test_enterprise_namespace.py` (30+ tests)
**Related Files**:
- `/src/wh/enterprise/namespace.py`
- `/src/wh/cli/namespace.py`
- `/src/wh/cli/main.py`
- `/src/wh/wns/dht.py`
- `/tests/unit/test_enterprise_namespace.py`
- `/docs/enterprise/multi-tenancy.md`
**Systemic Notes**: Namespaces provide DHT isolation so different teams can use same codes without conflict.

---

### FIX-013: Fix playwright import error in integration tests
**Date**: 2026-01-23
**Issue**: Test collection failed with NameError when playwright not installed
**Root Cause**: Type annotations for Browser and Page used even when playwright import failed
**Fix Applied**: Added stub type assignments (`Page = None`, `Browser = None`) in except block
**Tests Added**: N/A (fix to test infrastructure)
**Related Files**:
- `/tests/integration/test_discovery_site.py`
**Systemic Notes**: When using conditional imports for optional dependencies, always provide stub types for annotations.

---

### FIX-014: Update README with accurate test counts and complete commands
**Date**: 2026-01-23
**Issue**: README documented outdated test counts and missing command references
**Root Cause**: Documentation not updated after adding enterprise features and additional tools
**Fix Applied**:
- Updated Python test count from 745 to 959
- Added 8 additional network tools (telnet, ftp, nmap, traceroute, dns, mount, vnc, rdp)
- Added Namespace Commands table for enterprise multi-tenancy
**Tests Added**: N/A (documentation update)
**Related Files**:
- `/README.md`
**Systemic Notes**: Test counts and command references should be updated as part of feature release process.

---

### FIX-015: Remove duplicate lowercase plan.md from git tracking
**Date**: 2026-01-23
**Issue**: Git tracking both PLAN.md and plan.md causing conflicts on macOS
**Root Cause**: Case-sensitive git on case-insensitive macOS filesystem
**Fix Applied**: Removed lowercase `plan.md` from git tracking using `git rm --cached`
**Tests Added**: N/A (git fix)
**Related Files**:
- `plan.md` (deleted from git)
- `PLAN.md` (retained)
**Systemic Notes**: Always use consistent casing for filenames. Consider adding .gitattributes to enforce filename conventions.

---

<!-- Add new fixes above this line -->
