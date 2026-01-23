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

<!-- Add new fixes above this line -->
