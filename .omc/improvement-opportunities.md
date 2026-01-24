# Improvement Opportunities

> Generated: 2026-01-24
> Last Updated: 2026-01-24

## Purpose

This document tracks systemic improvement opportunities identified from FIXES.md patterns, baseline metrics, and architectural review. It prioritizes process improvements, automation, and quality enhancements that prevent recurring issues.

## Baseline Metrics (from Phase A.0)

**Verified on**: 2026-01-24

### Test Counts
- **Python tests**: 1338 (verified with `pytest --collect-only`)
- **Browser extension tests**: 552
- **Total tests**: 1890
- **Test breakdown** (from tests/README.md):
  - Unit: ~800 tests
  - Functional: ~200 tests
  - Integration: ~250 tests
  - Performance: ~50 tests
  - Browser: 552 tests

### Coverage
- **Overall coverage**: ~44% (estimated)
- **Core modules**: Higher coverage
- **CLI tools**: Lower coverage (~20%), requires integration testing

### Features
- **CLI tools with dilation**: 19 (ssh, scp, sftp, netcat, curl, wget, telnet, ftp, nmap, traceroute, dns, mount, vnc, rdp, rsync, dig, host, ping, iperf)
- **Enterprise modules**: 5 (auth, audit, policy, rate_limiter, namespace)
- **Web server integrations**:
  - Complete: Caddy (Go plugin), Discovery Site
  - Documented: Nginx, Apache, HAProxy, Traefik, Squid

### Project Status
- **Current Version**: 0.4.0
- **Current Phase**: Phase 5 (Web Server Integration) - Complete
- **Phases Complete**: 1-5
- **Next Phase**: Phase 6 (Enterprise Features) - Design phase

## Systemic Patterns from FIXES.md

### Pattern 1: Documentation Sync Issues
- **Occurrences**: FIX-004, FIX-014
- **Root Cause**: Test counts and command references not updated when tests/features added
- **Impact**: Misleading documentation, confusion about project capabilities
- **Improvement**: Add CI check to verify test counts match documentation
- **Related Script**: `/scripts/verify_test_counts.py` (already exists, needs CI integration)
- **Additional Actions**:
  - Add documentation update to feature completion checklist
  - Consider auto-generating CLI command tables from code

### Pattern 2: Version Mismatch
- **Occurrences**: FIX-002
- **Root Cause**: Version bumps not synchronized across multiple package files
- **Impact**: Confusion about canonical version, potential release issues
- **Improvement**: Add pre-commit hook or CI check for version sync
- **Files to Monitor**:
  - `/pyproject.toml` (Python package)
  - `/browser-extension/manifest.json` (extension)
  - `/discovery-site/package.json` (discovery site)
- **Additional Actions**:
  - Document version bump process
  - Consider single source of truth with automatic propagation

### Pattern 3: Missing Tests for Edge Cases
- **Occurrences**: FIX-013
- **Root Cause**: Optional dependencies cause import failures at test collection time
- **Impact**: Test collection fails without optional dependencies installed
- **Improvement**: Use proper conditional imports with stub types
- **Best Practice Documented**: Always provide `Type = None` in except blocks
- **Additional Actions**:
  - Document optional dependencies clearly
  - Add TYPE_CHECKING import guard examples to developer docs

### Pattern 4: Missing Documentation for Release Requirements
- **Occurrences**: FIX-005, FIX-007
- **Root Cause**: No checklist for extension publishing requirements
- **Impact**: Delays in release, blocked publication
- **Improvement**: Create comprehensive release checklist in CONTRIBUTING.md
- **Required Assets**:
  - Privacy policy (both in-repo and web-accessible)
  - Store descriptions (short and full)
  - Screenshots and promotional images
  - Developer account setup instructions

### Pattern 5: Placeholder Values in Documentation
- **Occurrences**: FIX-003
- **Root Cause**: Release process doesn't verify placeholders are filled
- **Impact**: Unprofessional appearance, confusion
- **Improvement**: Add placeholder detection to CI or pre-release checklist
- **Search Patterns**: XX, TODO, FIXME, TBD, YYYY-MM-DD

## Categories

### Critical (Security, breaking issues)
- None identified currently

### High (Reliability, consistency)
1. **Enable test count verification in CI**
   - Script exists: `/scripts/verify_test_counts.py`
   - Action: Add to GitHub Actions workflow
   - Impact: Prevents documentation drift automatically
   - Effort: Low (1-2 hours)

2. **Add version sync verification to CI**
   - Action: Create script to compare pyproject.toml with manifest.json and package.json
   - Impact: Prevents version mismatch during releases
   - Effort: Low (2-3 hours)

3. **Create comprehensive release checklist**
   - Action: Document all steps in CONTRIBUTING.md
   - Sections: Version bumping, testing, documentation, store assets, publishing
   - Impact: Streamlines release process, prevents missing steps
   - Effort: Medium (3-4 hours)

### Medium (Developer experience)
1. **Add AGENTS.md for better codebase navigation**
   - Action: Document module hierarchy, key components, common workflows
   - Impact: Faster onboarding, easier code discovery
   - Effort: Medium (4-5 hours)

2. **Document optional dependencies clearly**
   - Action: Create section in README and CONTRIBUTING.md
   - List: playwright, ldap3, any future optional deps
   - Impact: Clearer development setup
   - Effort: Low (1 hour)

3. **Add TYPE_CHECKING import guard examples**
   - Action: Add to developer documentation with examples
   - Impact: Prevents Pattern 3 (conditional import issues)
   - Effort: Low (1 hour)

4. **Create feature completion checklist template**
   - Action: Template in .github or docs/
   - Includes: Tests, docs, version updates, changelog entry
   - Impact: More consistent feature completion
   - Effort: Low (1-2 hours)

### Low (Nice to have)
1. **Add test coverage badges to README**
   - Action: Integrate coverage.py with CI, add shields.io badges
   - Impact: Visibility into test coverage trends
   - Effort: Low (2-3 hours)

2. **Create architecture diagram**
   - Action: Diagram showing components (CLI, daemon, DHT, integrations)
   - Format: Mermaid or similar markdown-embeddable
   - Impact: Easier understanding of system architecture
   - Effort: Medium (3-4 hours)

3. **Add placeholder detection pre-commit hook**
   - Action: Script to search for common placeholders
   - Impact: Prevents Pattern 5 (placeholder values)
   - Effort: Low (1-2 hours)

4. **Auto-generate CLI command tables**
   - Action: Script to extract Click commands and generate markdown tables
   - Impact: Always accurate command documentation
   - Effort: Medium (4-5 hours)

## Action Items (Prioritized)

### Phase 1: Quick Wins (Total: ~8-10 hours)
1. Enable verify_test_counts.py in CI workflow
2. Add version sync check script and CI integration
3. Document optional dependencies in README
4. Create release checklist in CONTRIBUTING.md

### Phase 2: Developer Experience (Total: ~10-12 hours)
1. Create AGENTS.md for codebase navigation
2. Add TYPE_CHECKING import guard examples to docs
3. Create feature completion checklist template
4. Add test coverage badges

### Phase 3: Polish (Total: ~8-10 hours)
1. Create architecture diagram
2. Add placeholder detection hook
3. Auto-generate CLI command tables

## Tracking

Changes to this document should be committed when:
- New systemic patterns identified from FIXES.md
- Action items completed (move to "Completed" section)
- Baseline metrics updated
- New improvement opportunities identified

### Completed
None yet.
