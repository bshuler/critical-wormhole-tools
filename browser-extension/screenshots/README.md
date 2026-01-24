# Browser Extension Screenshots for Store Submission

This directory contains screenshots for Chrome Web Store and Firefox Add-ons submission.

## Required Screenshots

You need to capture the following screenshots manually:

1. **popup-connected.png** - Extension popup showing active connection
2. **viewer-page.png** - Browser viewing a wh:// URL successfully
3. **settings-page.png** - Settings/options page
4. **address-bar.png** - Omnibox integration (typing "wh" in address bar)

## Store Requirements

### Chrome Web Store
- **Dimensions**: 1280x800 pixels (or 640x400 pixels)
- **Format**: PNG or JPEG
- **Minimum**: 2 screenshots required
- **Maximum**: 5 screenshots allowed
- **File size**: Max 5 MB per screenshot

### Firefox Add-ons
- **Dimensions**: 1280x720 pixels recommended (or any 16:9 aspect ratio)
- **Format**: PNG or JPEG
- **Minimum**: 1 screenshot required
- **Maximum**: 10 screenshots allowed
- **File size**: Max 5 MB per screenshot

**Recommendation**: Use 1280x800 for both stores (works for both Chrome and Firefox).

---

## Screenshot Capture Instructions

### Prerequisites

1. **Install the extension locally**:
   ```bash
   cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget/browser-extension
   npm run build
   ```

2. **Load in Chrome/Edge**:
   - Navigate to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `dist/chrome` directory

3. **Load in Firefox**:
   - Navigate to `about:debugging#/runtime/this-firefox`
   - Click "Load Temporary Add-on"
   - Select the `manifest.json` from `dist/firefox` directory

4. **Ensure wormhole daemon is running** (for connected screenshots):
   ```bash
   wh daemon --api
   ```

### Screenshot 1: popup-connected.png

**Purpose**: Show the extension popup with connection status.

**Steps**:
1. Ensure daemon is running and healthy
2. Click the Wormhole Browser extension icon in the toolbar
3. Wait for status to show "Connected" or "Ready"
4. Optionally: Enter a test address like "7-guitar-sunset" in the input field
5. Take screenshot at **1280x800 pixels**

**What to show**:
- Extension popup open
- Status indicator showing connected state
- "Navigate to Address" input field
- Omnibox tip visible

**Screenshot area**: Capture the popup window plus some surrounding browser chrome to show context.

---

### Screenshot 2: viewer-page.png

**Purpose**: Show the browser successfully viewing a wormhole address.

**Steps**:
1. In the browser, type `wh` in the address bar and press Tab
2. Type a wormhole address (e.g., `7-guitar-sunset` or `example.wns`)
3. Press Enter to navigate
4. Wait for the page to load in the viewer
5. Take screenshot at **1280x800 pixels**

**Alternative if no test site available**:
1. Use the test server from the extension directory:
   ```bash
   cd browser-extension
   python test-server.py
   ```
2. Navigate to the wormhole address it provides

**What to show**:
- Address bar showing `wh://address` or the viewer URL
- Successfully loaded content in the viewer frame
- Wormhole navigation UI (if visible)

**Screenshot area**: Full browser window showing address bar, content, and extension icon.

---

### Screenshot 3: settings-page.png

**Purpose**: Show the extension settings/options page.

**Steps**:
1. Right-click the Wormhole Browser extension icon
2. Select "Options" or click "Settings" link from popup
3. Settings page opens in a new tab
4. Optionally: Expand the "Advanced" section to show more features
5. Take screenshot at **1280x800 pixels**

**What to show**:
- Settings page header
- Relay Servers section
- Security settings (Code Length)
- Daemon configuration
- Optionally: Advanced section expanded

**Screenshot area**: Full browser tab showing the complete settings page. Scroll to show important sections if needed.

---

### Screenshot 4: address-bar.png

**Purpose**: Demonstrate the omnibox integration feature.

**Steps**:
1. Click in the browser address bar
2. Type `wh` and press **Tab** (or Space in Firefox)
3. The address bar should change to "Search Wormhole Browser"
4. Type a sample address like `example.wns` or `7-guitar-sunset`
5. Take screenshot at **1280x800 pixels** before pressing Enter

**What to show**:
- Address bar in "wormhole search mode" with suggestion
- The keyword `wh` trigger visible
- Example address typed in

**Screenshot area**: Upper portion of browser window focusing on the address bar.

---

## Taking Screenshots

### macOS
1. **Full window**: `Cmd + Shift + 4`, then press `Space`, click window
2. **Selection**: `Cmd + Shift + 4`, drag to select area
3. Screenshots save to Desktop by default

### Windows
1. **Snipping Tool**: Search for "Snipping Tool" in Start menu
2. **Game Bar**: `Win + Alt + PrtScn` (saves to Videos/Captures)
3. **Snip & Sketch**: `Win + Shift + S`

### Linux
1. **GNOME**: `PrtScn` or `Shift + PrtScn` for area
2. **KDE**: Use Spectacle tool
3. **Command line**: `scrot` or `gnome-screenshot`

### Browser DevTools for Exact Size
1. Open DevTools (`F12`)
2. Click "Toggle device toolbar" (Responsive Design Mode)
3. Set viewport to **1280x800**
4. Zoom out if needed to fit popup/page
5. Take screenshot

---

## Resizing Screenshots

If your screenshots are not exactly 1280x800:

### Using ImageMagick (command line)
```bash
# Install on macOS
brew install imagemagick

# Resize maintaining aspect ratio
convert input.png -resize 1280x800 output.png

# Resize and crop to exact size
convert input.png -resize 1280x800^ -gravity center -extent 1280x800 output.png
```

### Using GIMP (GUI)
1. Open image in GIMP
2. Image > Scale Image
3. Set width to 1280, height to 800
4. Export as PNG

### Online Tools
- [ResizeImage.net](https://resizeimage.net/)
- [ILoveIMG](https://www.iloveimg.com/resize-image)

---

## File Naming Convention

Save screenshots with these exact names:

```
screenshots/
├── popup-connected.png      (Extension popup)
├── viewer-page.png          (Browsing a wh:// URL)
├── settings-page.png        (Settings/options page)
└── address-bar.png          (Omnibox integration)
```

---

## Quality Checklist

Before uploading to stores, verify each screenshot:

- [ ] **Correct dimensions**: 1280x800 px
- [ ] **Clear and readable**: Text is sharp, not blurry
- [ ] **No sensitive data**: No personal info, tokens, or private addresses visible
- [ ] **Consistent UI**: Extension UI looks polished and complete
- [ ] **Good lighting**: Not too dark or washed out
- [ ] **Proper context**: Shows the feature in use, not just empty states
- [ ] **File size**: Under 5 MB per image
- [ ] **Format**: PNG (preferred) or JPEG

---

## Store Submission Order

### Recommended Screenshot Order for Store Listings

1. **viewer-page.png** - Lead with the main feature (browsing wormhole URLs)
2. **popup-connected.png** - Show the extension in action
3. **address-bar.png** - Demonstrate omnibox convenience
4. **settings-page.png** - Show advanced configuration options

This order tells a story: "Browse wormhole sites → Use the extension → Quick access → Customize settings"

---

## Testing Before Submission

1. **View at actual size**: Open screenshots at 100% zoom to verify clarity
2. **Show to others**: Get feedback on what's confusing or unclear
3. **Compare to successful extensions**: Look at other browser extensions' screenshots for inspiration
4. **Mobile preview**: Some users browse stores on mobile - check readability at small sizes

---

## Submission Notes

### Chrome Web Store
- Screenshots appear in carousel on store listing
- First screenshot is used as the main preview
- Captions are optional but recommended
- Review time: 2-7 days typically

### Firefox Add-ons
- Screenshots shown in a grid on listing page
- Captions strongly recommended (up to 250 characters each)
- Can upload different screenshots for desktop vs mobile
- Review time: 24-48 hours typically

---

## Additional Assets Needed

Beyond screenshots, you'll also need:

### Promotional Images (see `/browser-extension/store-assets/`)
- **Small promo tile**: 440x280 px (Chrome Web Store)
- **Large marquee**: 920x680 px (optional, Chrome Web Store featured placement)
- **Icon**: Already created in `/browser-extension/icons/` (16, 32, 48, 128 px)

### Text Content (already created)
- **Short description**: See `store-assets/description-short.txt`
- **Full description**: See `store-assets/description-full.txt`
- **Privacy policy**: See `/browser-extension/PRIVACY.md` (must be hosted online)

---

## Questions?

If you encounter issues capturing screenshots:

1. Check that the extension is built: `npm run build`
2. Verify daemon is running: `wh daemon --api`
3. Test the extension works before screenshotting
4. Use browser DevTools responsive mode for exact sizing
5. Refer to store documentation:
   - [Chrome Web Store Images Guide](https://developer.chrome.com/docs/webstore/images/)
   - [Firefox Add-ons Image Guidelines](https://extensionworkshop.com/documentation/develop/create-an-appealing-listing/)

---

## Quick Start Command Summary

```bash
# Build extension
cd /Users/bshuler/code/wormhole_netcat_ssh_scp_sftp_copy_curl_wget/browser-extension
npm run build

# Start daemon (for connected screenshots)
wh daemon --api

# Start test server (for viewer screenshot)
python test-server.py

# Load extension in Chrome
# chrome://extensions/ > Developer mode ON > Load unpacked > Select dist/chrome

# Load extension in Firefox
# about:debugging > Load Temporary Add-on > Select dist/firefox/manifest.json

# Resize screenshots (if needed)
convert input.png -resize 1280x800^ -gravity center -extent 1280x800 output.png
```

---

**Ready to submit?** See the main store assets README at `/browser-extension/store-assets/README.md` for the complete submission checklist.
