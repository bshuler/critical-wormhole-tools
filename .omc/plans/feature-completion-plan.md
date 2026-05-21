# Critical Wormhole Tools - Feature Completion Plan

> Created: 2026-01-24
> Status: Ready for Execution
> Objective: 100% completion of all requested features

---

## 1. Requirements Summary

### 1.1 Original Request
Complete all requested features for Critical Wormhole Tools:
1. Update all documentation files following specified patterns
2. Implement testing pyramid approach (e2e failures -> lower-tier tests -> fix)
3. Document all fixes in FIXES.md with systemic analysis
4. Continue until 100% completion (no partial completion)
5. Action on improvement opportunities discovered

### 1.2 User Constraints
- NO time estimates or duration predictions
- 100% completion required
- Document improvements as discovered
- Follow testing pyramid methodology
- Track fixes for systemic patterns

### 1.3 Handling Missing Documentation Patterns

User specified patterns to check. Status:

| Pattern | Codebase Status | Action |
|---------|-----------------|--------|
| `**/SESSION*.md` | Not present | Session history exists in PLAN.md "Session History" section - KEEP AS IS |
| `**/COMPLETE*.md` | Not present | NOT NEEDED - ROADMAP.md tracks phase completion |
| `**/STATUS*.md` | Not present | NOT NEEDED - PLAN.md "Current State" fulfills this purpose |
| `**/DEPLOY*.md` | Not present | CREATE NEW: `/docs/DEPLOYMENT.md` with deployment instructions |
| `**/ROLLOUT*.md` | Not present | NOT NEEDED - CHANGELOG.md tracks releases |

### 1.4 Current Project State

| Metric | Documented Value | Source | Action |
|--------|------------------|--------|--------|
| Python Tests | 791 | PLAN.md | **VERIFY with Step A.0** |
| Python Tests | 959 | FIX-014 (README update) | **VERIFY with Step A.0** |
| Browser Extension Tests | 552 | PLAN.md | Verify separately |
| CLI Tools with Dilation | All 19 | PLAN.md | No action needed |
| NPM Packages | 4 packages (see list below) | packages/ directory | No action needed |
| Documented Fixes | FIX-001 through FIX-015 | FIXES.md | Continue from FIX-016 |
| Phase 5 Status | PLAN.md: "In Progress" / ROADMAP.md: "COMPLETE" | Discrepancy | **RECONCILE in Phase A** |

**NPM Packages (explicit list):**
1. `@wormhole-tools/spake2` - `/packages/spake2/`
2. `@wormhole-tools/mailbox` - `/packages/mailbox/`
3. `@wormhole-tools/dilation` - `/packages/dilation/`
4. `@wormhole-tools/protocol` - `/packages/protocol/`

---

## 2. Concrete Acceptance Criteria

### 2.1 Binary Completion Checklist (PASS/FAIL)

Before claiming completion, ALL of these must pass:

- [ ] `pytest` exit code is 0 (all tests pass)
- [ ] `make lint` exit code is 0 (no linting errors)
- [ ] Test count in PLAN.md equals actual count from `pytest --collect-only`
- [ ] Version in `pyproject.toml` matches `browser-extension/manifest.json` and `discovery-site/package.json`
- [ ] Every fix applied has a corresponding FIXES.md entry (FIX-016+)
- [ ] All improvement opportunities documented in `/.omc/improvement-opportunities.md`
- [ ] Phase 5 status reconciled between PLAN.md and ROADMAP.md
- [ ] Standalone binaries build for all platforms (Linux, macOS, Windows)
- [ ] Binary CI workflow exists and passes

### 2.2 Documentation Updates
- [ ] All README.md files updated with accurate information
- [ ] PLAN.md updated with current test counts and status
- [ ] `/docs/DEPLOYMENT.md` created with deployment instructions
- [ ] SECURITY.md reviewed and current
- [ ] ROADMAP.md reflects actual implementation status
- [ ] All TEST*.md files accurate
- [ ] PHASE6_DESIGN.md aligned with implementation

### 2.3 Testing Pyramid Implementation
- [ ] When e2e test fails, unit test created first to isolate issue
- [ ] Unit tests prove the issue before fix is applied
- [ ] Test hierarchy: unit -> integration -> e2e
- [ ] All new tests documented in FIXES.md

### 2.4 Fix Tracking
- [ ] FIXES.md updated for all new fixes (FIX-016+)
- [ ] Systemic patterns identified and documented
- [ ] Root cause analysis for each fix
- [ ] Related files listed per fix

---

## 3. Implementation Steps

### Phase A: Documentation Audit and Update

**A.0: Verify Actual Test Count (MUST EXECUTE FIRST)**

```bash
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget
pytest --collect-only 2>&1 | tail -1
```

**Record this output as BASELINE.** All documentation updates must use this number.

Document finding in: `/.omc/improvement-opportunities.md` under "Baseline Metrics"

**A.1: Reconcile Phase 5 Status Discrepancy**
- PLAN.md says: "Phase 5 (Web Server Integration) - In Progress"
- ROADMAP.md says: "Phase 5: Web Server Integration (v0.5.0) COMPLETE"

Actions:
1. READ `/PLAN.md` line 4-6 header section
2. READ `/ROADMAP.md` Phase 5 section
3. DETERMINE which is accurate by checking:
   - Caddy plugin implementation status
   - Integration documentation completeness
4. UPDATE the incorrect document to match reality
5. DOCUMENT change in `/.omc/improvement-opportunities.md`

**A.2: Update Test Counts in PLAN.md**
- File: `/PLAN.md`
- Actions:
  1. READ line 25 (current documented count)
  2. VERIFY against A.0 baseline
  3. UPDATE to match actual count
  4. UPDATE "Last Updated" date to 2026-01-24

**A.3: Review and Update Core Documentation**

For EACH file below, perform these concrete actions:
1. **READ** the file completely
2. **VERIFY** version numbers match pyproject.toml (0.4.0)
3. **VERIFY** test counts match A.0 baseline
4. **VERIFY** all referenced files exist
5. **UPDATE** any inaccurate information found
6. **DOCUMENT** changes made in `/.omc/improvement-opportunities.md`

Files:
- `/PLAN.md` - Current state, test counts, session history
- `/ROADMAP.md` - Phase statuses match implementation
- `/SECURITY.md` - Version support current
- `/CHANGELOG.md` - Recent changes documented
- `/CONTRIBUTING.md` - Verify accuracy

**A.4: Create Missing Deployment Documentation**

Create `/docs/DEPLOYMENT.md` with:
- Docker deployment instructions
- PyPI installation
- System requirements
- Configuration options
- Environment variables

**A.5: Review Module Documentation**

For EACH file, perform the 6-step process from A.3:
- `/browser-extension/README.md`
- `/integrations/caddy/README.md`
- `/integrations/nginx/README.md`
- `/integrations/apache/README.md`
- `/integrations/haproxy/README.md`
- `/integrations/traefik/README.md`
- `/integrations/squid/README.md`
- `/integrations/nginx-native/README.md`
- `/integrations/traefik-native/README.md`
- `/mobile/README.md`
- `/packages/spake2/README.md`
- `/packages/mailbox/README.md`
- `/packages/dilation/README.md`
- `/packages/protocol/README.md`
- `/docs/enterprise/*.md`

**A.6: Review Test Documentation**

For EACH file:
- `/docs/protocol/TEST_VECTORS.md`
- `/discovery-site/EDGE_CASE_TEST_RESULTS.md`
- `/discovery-site/FINAL_EDGE_CASE_TEST_RESULTS.md`
- `/integrations/caddy/tests/README.md`
- `/tests/performance/README.md`

### Phase B: Testing Pyramid Assessment

**B.1: Analyze Current Test Structure**
```
tests/
├── unit/           # Fast, isolated tests
├── functional/     # Component tests
├── integration/    # Network tests
└── performance/    # Benchmark tests
```

**B.2: Identify Test Gaps**
- Run full test suite and capture any failures
- For each failure, identify if lower-tier test exists
- Create unit tests for any issues found at higher tiers

**B.3: Create /tests/README.md**

Since `/tests/README.md` does not exist, create it with this structure:

```markdown
# Test Suite Documentation

## Overview
This directory contains the test suite for Critical Wormhole Tools.

## Test Pyramid

| Tier | Directory | Description | Run Command |
|------|-----------|-------------|-------------|
| Unit | tests/unit/ | Fast, isolated tests | `pytest tests/unit/` |
| Functional | tests/functional/ | Component tests | `pytest tests/functional/` |
| Integration | tests/integration/ | Network tests | `pytest tests/integration/` |
| Performance | tests/performance/ | Benchmark tests | `pytest tests/performance/` |

## Running Tests

### All Tests
```bash
make test
# or
pytest
```

### By Category
```bash
pytest tests/unit/           # Unit tests only
pytest tests/functional/     # Functional tests only
pytest tests/integration/    # Integration tests only
pytest tests/performance/    # Performance tests only
```

### With Coverage
```bash
make test-coverage
# or
pytest --cov=wh --cov-report=html
```

## Test Markers

- `@pytest.mark.slow` - Tests that take >1s
- `@pytest.mark.network` - Tests requiring network
- `@pytest.mark.optional` - Tests for optional dependencies

## Writing New Tests

1. **Unit tests first** - When fixing a bug, write a unit test that reproduces it
2. **Isolation** - Unit tests should not require network or external services
3. **Naming** - Use `test_<module>_<function>_<scenario>.py` format
4. **Fixtures** - Prefer fixtures over setUp/tearDown
```

### Phase C: Run Tests and Fix Issues

**C.1: Run Full Test Suite**
```bash
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget
pytest -v --tb=short 2>&1 | tee /tmp/test-output.txt
echo "Exit code: $?"
```

**C.2: For Each Failure**
1. Document in FIXES.md as FIX-0XX
2. Create unit test to prove issue
3. Apply fix
4. Verify unit test passes
5. Verify original failing test passes

**C.3: Run Linting**
```bash
make lint 2>&1 | tee /tmp/lint-output.txt
echo "Exit code: $?"
```

### Phase D: Fix Documentation

**D.1: Update FIXES.md**
- Add all new fixes with:
  - Date: 2026-01-24
  - Issue description
  - Root cause analysis
  - Fix applied
  - Tests added
  - Related files (full paths)
  - Systemic notes

**D.2: Identify Systemic Patterns**
Review FIX-001 through FIX-015 and new fixes for patterns:
- Documentation sync issues
- Version inconsistencies
- Test infrastructure gaps
- Import/dependency issues

Document patterns in `/.omc/improvement-opportunities.md`

### Phase E: Improvement Opportunities

**E.1: Document Discovered Improvements**
File: `/.omc/improvement-opportunities.md`

Structure:
```markdown
# Improvement Opportunities

> Generated: 2026-01-24
> Last Updated: [update during execution]

## Baseline Metrics (from A.0)
- Python tests: [actual count]
- Browser extension tests: 552
- Coverage: ~44%

## Categories

### Critical (Security, breaking issues)
[List items]

### High (Reliability, consistency)
[List items]

### Medium (Developer experience)
[List items]

### Low (Nice to have)
[List items]

## Discovered During Execution
[Add items as discovered]
```

**E.2: Prioritize Improvements**
- Critical: Security, breaking issues
- High: Reliability, consistency
- Medium: Developer experience
- Low: Nice to have

**E.3: Create Action Items**
For each improvement, document:
- Description
- Impact
- Dependencies
- Proposed solution

### Phase G: Create Standalone Binaries

**G.0: Overview**

Create standalone executables for all CLI tools that can be deployed without Python installed. This enables zero-dependency distribution for end users.

**Targets:**
- Linux (x86_64, arm64)
- macOS (x86_64, arm64/Apple Silicon)
- Windows (x86_64)

**G.1: Add PyInstaller Configuration**

Create `/packaging/binaries/` directory with build infrastructure:

```
packaging/binaries/
├── README.md              # Binary build documentation
├── build.py               # Cross-platform build script
├── hooks/                 # PyInstaller hooks for dependencies
│   └── hook-wh.py
├── specs/                 # PyInstaller spec files
│   └── wh.spec
└── assets/                # Icons and metadata
    ├── wh.icns            # macOS icon
    ├── wh.ico             # Windows icon
    └── wh.png             # Linux icon
```

**G.2: Create PyInstaller Spec File**

File: `/packaging/binaries/specs/wh.spec`

Key configuration:
- Single-file executable (`--onefile`)
- Include all CLI subcommands
- Bundle required data files (wordlist, etc.)
- Hidden imports for all wh.* modules
- Platform-specific optimizations

**G.3: Create Build Script**

File: `/packaging/binaries/build.py`

Features:
- Cross-platform build (auto-detect OS)
- Version extraction from pyproject.toml
- Output naming: `wh-{version}-{os}-{arch}`
- Compression and stripping
- Code signing placeholders

Build command:
```bash
cd /packaging/binaries
python build.py
# Output: dist/wh-0.4.0-linux-x86_64
#         dist/wh-0.4.0-darwin-arm64
#         dist/wh-0.4.0-windows-x86_64.exe
```

**G.4: Add CI Workflow for Binary Builds**

File: `/.github/workflows/binaries.yml`

Matrix build for all platforms:
```yaml
name: Build Binaries
on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        arch: [x64]
        include:
          - os: macos-latest
            arch: arm64
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pyinstaller
      - name: Build binary
        run: python packaging/binaries/build.py
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: wh-${{ matrix.os }}-${{ matrix.arch }}
          path: packaging/binaries/dist/wh*
```

**G.5: Update Packaging README**

Add to `/packaging/README.md`:

| Package Type | Directory | Status | Install Command |
|--------------|-----------|--------|-----------------|
| Standalone Binary | `binaries/` | Ready | Download from releases |

Add build instructions for standalone binaries.

**G.6: Create Binary Documentation**

File: `/packaging/binaries/README.md`

Contents:
- Overview of standalone binary distribution
- Supported platforms and architectures
- Build instructions (local and CI)
- Installation instructions per platform
- Verification (checksums, signatures)
- Troubleshooting common issues

**G.7: Binary Acceptance Criteria**

- [ ] `wh --version` works on all platforms without Python
- [ ] All 19 CLI tools functional in binary
- [ ] Binary size reasonable (<100MB per platform)
- [ ] CI workflow builds all platforms successfully
- [ ] Checksums generated for each binary
- [ ] Documentation complete

**G.8: CLI Tools to Include in Binary**

All 19 tools must be functional:
1. `wh nc` - Netcat
2. `wh listen` - Listener
3. `wh ssh` - SSH client
4. `wh scp` - Secure copy
5. `wh sftp` - SFTP client
6. `wh curl` - HTTP client
7. `wh wget` - File download
8. `wh ping` - Latency measurement
9. `wh rsync` - Incremental sync
10. `wh proxy` - SOCKS5 proxy
11. `wh tunnel` - Port forwarding
12. `wh telnet` - Raw TCP
13. `wh ftp` - FTP client
14. `wh nmap` - Port scanning
15. `wh traceroute` - Hop analysis
16. `wh dns` - DNS queries
17. `wh mount` - FUSE mounting
18. `wh vnc` - VNC client
19. `wh rdp` - RDP client

Plus supporting commands:
- `wh daemon` - HTTP API daemon
- `wh relay` - Relay server
- `wh identity` - WNS identity management
- `wh namespace` - Namespace management

### Phase F: Final Verification

**F.1: Run All Verification Commands**
```bash
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget

# Test suite - must exit 0
pytest -v --tb=short
echo "pytest exit code: $?"

# Linting - must exit 0
make lint
echo "lint exit code: $?"

# Test count verification
pytest --collect-only 2>&1 | tail -1

# Extension tests
cd browser-extension && npm test
echo "npm test exit code: $?"

# Version check
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget
grep -E "^version" pyproject.toml
grep '"version"' browser-extension/manifest.json
grep '"version"' discovery-site/package.json
```

**F.2: Binary Checklist Verification**

Execute EACH check and record PASS/FAIL:

| Check | Command | Expected | Actual | Status |
|-------|---------|----------|--------|--------|
| pytest passes | `pytest; echo $?` | 0 | [record] | [ ] |
| lint passes | `make lint; echo $?` | 0 | [record] | [ ] |
| Test count matches | Compare A.0 with PLAN.md | Match | [record] | [ ] |
| Versions sync | grep version files | All 0.4.0 | [record] | [ ] |
| All fixes documented | Count FIX-016+ entries | >=0 | [record] | [ ] |
| Improvements documented | File exists | Yes | [record] | [ ] |
| Binary spec exists | `ls packaging/binaries/specs/wh.spec` | File exists | [record] | [ ] |
| Build script exists | `ls packaging/binaries/build.py` | File exists | [record] | [ ] |
| Binary CI workflow | `ls .github/workflows/binaries.yml` | File exists | [record] | [ ] |
| Binary builds locally | `python packaging/binaries/build.py` | Exit 0 | [record] | [ ] |

**F.3: Post-Completion Validation**
- PLAN.md "Last Updated" date is 2026-01-24
- All phase statuses in ROADMAP.md accurate
- FIXES.md has no placeholder entries
- Improvement opportunities documented
- `/tests/README.md` exists

---

## 4. Risk Identification and Mitigations

### Risk 1: Undiscovered Failing Tests
**Impact**: Incomplete completion
**Mitigation**:
- Run full test suite in clean environment
- Check CI/CD for any skipped or ignored tests
- Review test markers for xfail or skip

### Risk 2: Documentation Drift
**Impact**: Inaccurate documentation
**Mitigation**:
- Cross-reference code with docs
- Verify all CLI commands documented match implementation
- Check version numbers in multiple locations

### Risk 3: Incomplete Enterprise Features
**Impact**: PHASE6_DESIGN.md may describe features not implemented
**Mitigation**:
- Review each feature in design doc
- Verify corresponding code exists
- Mark incomplete features as "Planned" vs "Complete"

### Risk 4: External Dependencies
**Impact**: Browser extension publish blocked (no dev accounts)
**Mitigation**:
- Document as blocked, not incomplete
- Track in FIXES.md as FIX-007 notes

### Risk 5: Binary Size Too Large
**Impact**: Standalone binaries may exceed 100MB due to bundled dependencies
**Mitigation**:
- Use PyInstaller `--onefile` with UPX compression
- Exclude unused imports with careful hook configuration
- Consider Nuitka for smaller binaries if PyInstaller is too large

### Risk 6: Platform-Specific Binary Issues
**Impact**: Binary may not work on all target platforms
**Mitigation**:
- Use GitHub Actions matrix to build on each platform natively
- Test binaries on each platform before release
- Document minimum OS versions (e.g., macOS 11+, Ubuntu 20.04+)

### Risk 7: Hidden Import Failures
**Impact**: Binary crashes due to missing modules at runtime
**Mitigation**:
- Create comprehensive PyInstaller hooks for all wh.* modules
- Test all 19 CLI tools in the binary
- Document any optional dependencies (ldap3, etc.)

---

## 5. File Reference

### Core Documentation
| File | Purpose |
|------|---------|
| `/PLAN.md` | Main project plan, current state |
| `/FIXES.md` | Fix tracking log |
| `/SECURITY.md` | Security policy |
| `/ROADMAP.md` | Feature roadmap |
| `/CHANGELOG.md` | Version history |
| `/CONTRIBUTING.md` | Contribution guide |
| `/README.md` | Project documentation |

### New Files to Create
| File | Purpose |
|------|---------|
| `/docs/DEPLOYMENT.md` | Deployment instructions |
| `/tests/README.md` | Test suite documentation |
| `/.omc/improvement-opportunities.md` | Discovered improvements |
| `/packaging/binaries/README.md` | Binary build documentation |
| `/packaging/binaries/build.py` | Cross-platform build script |
| `/packaging/binaries/specs/wh.spec` | PyInstaller spec file |
| `/.github/workflows/binaries.yml` | Binary build CI workflow |

### Test Documentation
| File | Purpose |
|------|---------|
| `/docs/protocol/TEST_VECTORS.md` | Protocol test vectors |
| `/discovery-site/*TEST*.md` | Edge case test results |
| `/integrations/caddy/tests/README.md` | Caddy test docs |
| `/tests/performance/README.md` | Performance test docs |

### Enterprise Documentation
| File | Purpose |
|------|---------|
| `/docs/enterprise/PHASE6_DESIGN.md` | Enterprise design doc |
| `/docs/enterprise/authentication.md` | Auth docs |
| `/docs/enterprise/audit-logging.md` | Audit docs |
| `/docs/enterprise/rate-limiting.md` | Rate limit docs |
| `/docs/enterprise/multi-tenancy.md` | Multi-tenant docs |

### Module READMEs
| File | Purpose |
|------|---------|
| `/browser-extension/README.md` | Extension docs |
| `/integrations/caddy/README.md` | Caddy plugin docs |
| `/integrations/nginx/README.md` | Nginx config docs |
| `/integrations/apache/README.md` | Apache config docs |
| `/integrations/haproxy/README.md` | HAProxy config docs |
| `/integrations/traefik/README.md` | Traefik config docs |
| `/integrations/squid/README.md` | Squid config docs |
| `/integrations/nginx-native/README.md` | Nginx native module docs |
| `/integrations/traefik-native/README.md` | Traefik native plugin docs |
| `/mobile/README.md` | Mobile app docs |
| `/packages/spake2/README.md` | SPAKE2 package docs |
| `/packages/mailbox/README.md` | Mailbox package docs |
| `/packages/dilation/README.md` | Dilation package docs |
| `/packages/protocol/README.md` | Protocol package docs |
| `/packaging/README.md` | Packaging docs |

---

## 6. Commit Strategy

### Commit Categories
1. **docs:** - Documentation updates
2. **fix:** - Bug fixes with FIXES.md entries
3. **test:** - New or updated tests
4. **feat:** - New features (e.g., binary builds)
5. **ci:** - CI/CD workflow changes
6. **chore:** - Maintenance, cleanup

### Commit Message Format
```
<type>: <description>

- Specific change 1
- Specific change 2

Refs: FIX-0XX (if applicable)
```

### Recommended Commit Flow
1. `docs: Update PLAN.md with accurate test counts and current state`
2. `docs: Create DEPLOYMENT.md and tests/README.md`
3. `docs: Update README.md documentation`
4. `fix: [issue description]` (with FIXES.md entry)
5. `test: Add unit tests for [issue]`
6. `docs: Update FIXES.md with systemic patterns`
7. `feat: Add standalone binary build infrastructure`
8. `ci: Add binary build workflow for all platforms`
9. `chore: Final documentation review and cleanup`

---

## 7. Success Criteria

### Quantitative (Binary PASS/FAIL)
- `pytest` exit code = 0
- `make lint` exit code = 0
- `npm test` exit code = 0 (in browser-extension)
- Version 0.4.0 in all 3 locations
- Test count in PLAN.md = actual count
- Standalone binary builds successfully for current platform
- All 19 CLI tools work in binary (test with `./wh --help`)

### Qualitative
- All README files accurately describe their modules
- FIXES.md provides clear systemic insight
- Improvement opportunities are actionable
- Documentation enables new contributors

---

## 8. Execution Notes

### Start Command
```bash
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget
```

### Progress Tracking
Update this plan as work progresses:
- [ ] Phase A: Documentation Audit - NOT STARTED
  - [ ] A.0: Verify Actual Test Count
  - [ ] A.1: Reconcile Phase 5 Status
  - [ ] A.2: Update Test Counts
  - [ ] A.3: Core Documentation
  - [ ] A.4: Create DEPLOYMENT.md
  - [ ] A.5: Module Documentation
  - [ ] A.6: Test Documentation
- [ ] Phase B: Testing Pyramid - NOT STARTED
  - [ ] B.1: Analyze Structure
  - [ ] B.2: Identify Gaps
  - [ ] B.3: Create /tests/README.md
- [ ] Phase C: Test and Fix - NOT STARTED
  - [ ] C.1: Run Tests
  - [ ] C.2: Fix Failures
  - [ ] C.3: Run Linting
- [ ] Phase D: Fix Documentation - NOT STARTED
  - [ ] D.1: Update FIXES.md
  - [ ] D.2: Identify Patterns
- [ ] Phase E: Improvements - NOT STARTED
  - [ ] E.1: Document Improvements
  - [ ] E.2: Prioritize
  - [ ] E.3: Create Action Items
- [ ] Phase F: Verification - NOT STARTED
  - [ ] F.1: Run Verification Commands
  - [ ] F.2: Binary Checklist
  - [ ] F.3: Post-Completion Validation
- [ ] Phase G: Standalone Binaries - NOT STARTED
  - [ ] G.1: Add PyInstaller Configuration
  - [ ] G.2: Create PyInstaller Spec File
  - [ ] G.3: Create Build Script
  - [ ] G.4: Add CI Workflow
  - [ ] G.5: Update Packaging README
  - [ ] G.6: Create Binary Documentation
  - [ ] G.7: Verify Binaries Work

---

**End of Plan**

*To execute this plan, run `/start-work` in Claude Code*
