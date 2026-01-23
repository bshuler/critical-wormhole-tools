# Wormhole Mobile App

React Native mobile application for Wormhole Name System (WNS) browsing and peer-to-peer connections.

## Features

- Connect to peers using wormhole codes
- Browse WNS names (wh://name.tld URLs)
- Manage multiple identities
- Configure relay servers
- Discover peers via DHT
- Offline-first architecture

## Architecture

### Core Components

1. **WNS Browser** - Navigate to wh:// URLs, resolve names via DHT
2. **Identity Manager** - Create, import, export identity keypairs
3. **Peer Connector** - Establish connections using wormhole codes
4. **Settings** - Configure relays, DHT bootstrap nodes

### Technology Stack

- React Native (iOS & Android)
- Expo (for easier development)
- libsodium-wrappers (crypto)
- AsyncStorage (local persistence)
- React Navigation (routing)

### Communication with wh Daemon

The mobile app can operate in two modes:

1. **Standalone Mode** - Bundled libwormhole native module
2. **Daemon Mode** - Connect to local wh daemon via HTTP API (for testing on simulators)

## Project Structure

```
mobile/
├── src/
│   ├── screens/        # App screens
│   ├── components/     # Reusable UI components
│   ├── services/       # WNS, DHT, crypto services
│   ├── hooks/          # Custom React hooks
│   └── App.js          # Main navigation
├── android/            # Android native code
├── ios/                # iOS native code
├── __tests__/          # Jest tests
└── package.json
```

## Development

### Prerequisites

- Node.js 18+
- npm or yarn
- Expo CLI: `npm install -g expo-cli`
- For iOS: Xcode
- For Android: Android Studio

### Setup

```bash
cd mobile
npm install
```

### Run on Simulator

```bash
# iOS
npm run ios

# Android
npm run android

# Expo Go
npm start
```

### Run on Device

```bash
# iOS
npm run ios --device

# Android (with device connected via USB)
npm run android --device
```

## Building for Production

### iOS

```bash
eas build --platform ios
```

### Android

```bash
eas build --platform android
```

## Testing

```bash
# Unit tests
npm test

# E2E tests (detox)
npm run e2e
```

## Configuration

Edit `app.json` to configure:
- App name and slug
- Bundle identifiers
- Permissions (network, storage)
- Icons and splash screens

## Security Considerations

- Identity keys stored in secure keychain (iOS) or keystore (Android)
- No private keys transmitted over network
- Relay connections use TLS
- DHT queries use authenticated encryption

## Future Enhancements

- [ ] Push notifications for incoming connections
- [ ] Background file transfers
- [ ] Peer discovery via Bluetooth/NFC
- [ ] Integration with mobile wallet apps
- [ ] Offline DHT caching
- [ ] MetaMask mobile integration

## License

MIT
