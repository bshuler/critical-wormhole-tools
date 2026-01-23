# Discovery Site Inline Viewer Fix - Plan & Progress

## Problem Statement

The discovery site had a critical bug where connecting to a wormhole would fail with a "crowded" error. This happened because:

1. Discovery page (index.html) establishes wormhole connection
2. Page navigates to viewer.html (separate page load)
3. JavaScript context is lost, `activeConnections` Map becomes empty
4. Viewer.html calls `ensureConnection()` which tries to create NEW connection
5. Wormhole relay rejects with "crowded" error (3 sides trying to use same mailbox)

## Solution Implemented

Changed from multi-page navigation to single-page app (SPA) architecture:
- Viewer UI loads inline in the same page instead of navigating to viewer.html
- Original wormhole connection is preserved and reused
- No reconnection attempt needed

## Files Modified

### 1. discovery-site/src/index.html
- Added CSS styles for viewer components (loading, error, sandbox iframe)
- Added viewer container HTML elements (hidden by default)
- Added `body.viewing` class to hide discovery UI when viewing

### 2. discovery-site/src/app.js
- Replaced `navigateToViewer()` function (was: `window.location.href = 'viewer.html?...'`)
- Added inline viewer logic:
  - `showViewerLoading()` / `hideViewerLoading()` / `showViewerError()` / `hideViewer()`
  - `displayContent()` - sends content to sandbox iframe
  - `fetchViewerResource()` - fetches resources through wormhole
  - `viewerNavigateTo()` - handles internal navigation
  - `handleResourceRequest()` - handles sandbox resource requests
  - Message event listener for sandbox communication
  - Browser history (popstate) handling

### 3. discovery-site/tests/test_full_integration.py
- Updated `connect_to_wormhole()` to wait for sandbox visibility instead of URL change
- Updated `test_connect_to_wormhole` to check sandbox visibility instead of "viewer.html" in URL
- Updated `test_hash_link_behavior` to check sandbox visibility

### 4. discovery-site/src/lib/protocol/dilation.js
- Increased dilation timeout from 10s to 30s

### 5. src/wh/cli/listen.py
- Added `--dilate/--no-dilate` flag for file server mode

### 6. discovery-site/Makefile
- Updated test targets for integration tests

## New Files Created

### discovery-site/tests/
- `__init__.py` - Package init
- `conftest.py` - Pytest fixtures (wormhole_server, browser, page, page_with_tracking)
- `test_full_integration.py` - Main test suite (~20 tests)
- `utils/__init__.py` - Utils package init
- `utils/wormhole_server.py` - WormholeServer context manager
- `utils/console_tracker.py` - Console message tracking for tests

## Commits Created (Not Yet Pushed)

```
2a36ccb feat: Add dilation support for wh listen --serve
9792d88 fix: Load viewer inline instead of navigating to separate page
dd7ab42 feat: Add AWS infrastructure and Playwright tests for discovery site
```

## Current State

- All code changes complete
- Build succeeds (`npm run build`)
- 3 commits ready to push
- Git push failing due to authentication (needs GitHub token or SSH key)

## Test Categories

The test suite covers:
- **Connection Flow**: Discovery page loads, connect to wormhole, viewer loads content
- **JavaScript Execution**: Status indicator, click counter, dynamic content, toggle hidden
- **Navigation**: Internal links, hash links, query params
- **Resource Loading**: CSS styles, status indicator styling
- **Form Interaction**: Input filling
- **Storage APIs**: localStorage, sessionStorage
- **Advanced APIs**: WebRTC, WebSocket, Workers
- **Error Verification**: No JS errors on load, after interactions

## How to Test

1. Build the site:
   ```bash
   cd discovery-site && npm run build
   ```

2. Deploy to production (or serve locally)

3. Run integration tests:
   ```bash
   cd discovery-site && make test
   ```
   Or:
   ```bash
   cd discovery-site && xvfb-run -a python -m pytest tests/test_full_integration.py -v -s
   ```

## Key Architecture Change

**Before (Multi-Page):**
```
index.html → [connect] → navigate to viewer.html → [reconnect attempt] → FAILS
```

**After (Single-Page):**
```
index.html → [connect] → show viewer UI inline → [reuse connection] → SUCCESS
```

## Next Steps

1. Push commits to GitHub (requires authentication setup)
2. Deploy updated discovery site to production
3. Run full integration test suite against production
4. Verify all tests pass

## Environment

- Working directory: /home/developer/workspace
- Branch: main
- Remote: https://github.com/bshuler/critical-wormhole-tools.git
