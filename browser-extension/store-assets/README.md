# Store Assets for Browser Extension

This directory contains assets for Chrome Web Store and Firefox Add-ons submissions.

## Contents

### Text Content
- `description-short.txt` - Short description (max 132 chars for Chrome)
- `description-full.txt` - Full store listing description

### Images Required (TO BE CREATED)

#### Chrome Web Store
- `screenshots/` - At least 2 screenshots (1280x800 or 640x400 px)
- `promo-small.png` - Small promotional tile (440x280 px)
- `promo-large.png` - Large marquee promotional tile (920x680 px, optional)

#### Firefox Add-ons
- Same screenshots work for both stores
- Different promotional tile sizes may be needed

### Icons (Already in `/icons/`)
- `wormhole-16.png` (16x16)
- `wormhole-32.png` (32x32)
- `wormhole-48.png` (48x48)
- `wormhole-128.png` (128x128)

## Screenshot Guidelines

Screenshots should demonstrate:
1. Extension popup showing connection status
2. Browsing a wh:// URL successfully
3. WNS address resolution
4. Settings/options page

## Submission Checklist

### Chrome Web Store
- [ ] Developer account created ($5 one-time fee)
- [ ] Privacy policy URL ready (see /browser-extension/PRIVACY.md)
- [ ] Screenshots uploaded (min 2)
- [ ] Promotional images uploaded
- [ ] Extension .zip packaged

### Firefox Add-ons
- [ ] Developer account created (free)
- [ ] Extension signed
- [ ] Screenshots uploaded
- [ ] Source code ready if requested

## Packaging Commands

```bash
# Build and package for Chrome
npm run package:chrome

# Build and package for Firefox
npm run package:firefox
```

## Notes

- Chrome review typically takes 2-7 days
- Firefox review typically takes 24-48 hours
- Both require privacy policy to be accessible online
