import * as TaskManager from 'expo-task-manager';
import * as BackgroundFetch from 'expo-background-fetch';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { notifyIncomingConnection, notifyConnectionEstablished } from './notifications';

const BACKGROUND_FETCH_TASK = 'wormhole-background-listener';
const PENDING_CONNECTIONS_KEY = '@wormhole/pending_connections';
const ACTIVE_CODES_KEY = '@wormhole/active_codes';

/**
 * Define the background task
 * This runs periodically to check for incoming connections
 */
TaskManager.defineTask(BACKGROUND_FETCH_TASK, async () => {
    try {
        const result = await checkForIncomingConnections();

        if (result.hasNewConnections) {
            return BackgroundFetch.BackgroundFetchResult.NewData;
        }
        return BackgroundFetch.BackgroundFetchResult.NoData;
    } catch (error) {
        console.error('Background fetch error:', error);
        return BackgroundFetch.BackgroundFetchResult.Failed;
    }
});

/**
 * Check for incoming connections
 * This is called both by the background task and can be called manually
 */
async function checkForIncomingConnections() {
    // Get active wormhole codes that we're listening for
    const activeCodes = await getActiveCodes();

    if (activeCodes.length === 0) {
        return { hasNewConnections: false, connections: [] };
    }

    const newConnections = [];

    for (const codeInfo of activeCodes) {
        try {
            // TODO: Replace with actual wormhole protocol check
            // This would connect to the mailbox server and check for peers
            const connectionCheck = await checkCodeForConnections(codeInfo.code);

            if (connectionCheck.hasPendingPeer) {
                newConnections.push({
                    code: codeInfo.code,
                    peerInfo: connectionCheck.peerInfo,
                    timestamp: Date.now(),
                });

                // Notify the user
                notifyIncomingConnection(codeInfo.code, connectionCheck.peerInfo);
            }
        } catch (error) {
            console.error(`Error checking code ${codeInfo.code}:`, error);
        }
    }

    if (newConnections.length > 0) {
        // Store pending connections for the app to handle when opened
        await storePendingConnections(newConnections);
    }

    return {
        hasNewConnections: newConnections.length > 0,
        connections: newConnections,
    };
}

/**
 * Placeholder for actual wormhole connection check
 * TODO: Implement using wormhole protocol
 */
async function checkCodeForConnections(code) {
    // This is a placeholder - actual implementation would:
    // 1. Connect to the mailbox server
    // 2. Check if there's a peer waiting with this code
    // 3. Return peer info if found

    return {
        hasPendingPeer: false,
        peerInfo: null,
    };
}

/**
 * Register the background fetch task
 */
export async function registerBackgroundListener() {
    try {
        await BackgroundFetch.registerTaskAsync(BACKGROUND_FETCH_TASK, {
            minimumInterval: 60 * 15, // 15 minutes (minimum on iOS)
            stopOnTerminate: false,   // Continue after app is closed (Android)
            startOnBoot: true,        // Start after device reboot (Android)
        });
        console.log('Background listener registered');
        return true;
    } catch (error) {
        console.error('Failed to register background listener:', error);
        return false;
    }
}

/**
 * Unregister the background fetch task
 */
export async function unregisterBackgroundListener() {
    try {
        await BackgroundFetch.unregisterTaskAsync(BACKGROUND_FETCH_TASK);
        console.log('Background listener unregistered');
        return true;
    } catch (error) {
        console.error('Failed to unregister background listener:', error);
        return false;
    }
}

/**
 * Check if background listener is registered
 */
export async function isBackgroundListenerRegistered() {
    const status = await BackgroundFetch.getStatusAsync();
    const isRegistered = await TaskManager.isTaskRegisteredAsync(BACKGROUND_FETCH_TASK);

    return {
        isRegistered,
        status: getBackgroundFetchStatusString(status),
    };
}

/**
 * Get background fetch status as string
 */
function getBackgroundFetchStatusString(status) {
    switch (status) {
        case BackgroundFetch.BackgroundFetchStatus.Restricted:
            return 'restricted';
        case BackgroundFetch.BackgroundFetchStatus.Denied:
            return 'denied';
        case BackgroundFetch.BackgroundFetchStatus.Available:
            return 'available';
        default:
            return 'unknown';
    }
}

/**
 * Add a wormhole code to listen for
 */
export async function addActiveCode(code, metadata = {}) {
    const activeCodes = await getActiveCodes();

    // Check if code already exists
    if (activeCodes.find(c => c.code === code)) {
        return false;
    }

    activeCodes.push({
        code,
        createdAt: Date.now(),
        ...metadata,
    });

    await AsyncStorage.setItem(ACTIVE_CODES_KEY, JSON.stringify(activeCodes));
    return true;
}

/**
 * Remove a wormhole code from listening
 */
export async function removeActiveCode(code) {
    const activeCodes = await getActiveCodes();
    const filtered = activeCodes.filter(c => c.code !== code);
    await AsyncStorage.setItem(ACTIVE_CODES_KEY, JSON.stringify(filtered));
}

/**
 * Get all active codes we're listening for
 */
export async function getActiveCodes() {
    try {
        const stored = await AsyncStorage.getItem(ACTIVE_CODES_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Failed to get active codes:', error);
        return [];
    }
}

/**
 * Clear all active codes
 */
export async function clearActiveCodes() {
    await AsyncStorage.removeItem(ACTIVE_CODES_KEY);
}

/**
 * Store pending connections for later handling
 */
async function storePendingConnections(connections) {
    const existing = await getPendingConnections();
    const updated = [...existing, ...connections];
    await AsyncStorage.setItem(PENDING_CONNECTIONS_KEY, JSON.stringify(updated));
}

/**
 * Get pending connections
 */
export async function getPendingConnections() {
    try {
        const stored = await AsyncStorage.getItem(PENDING_CONNECTIONS_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Failed to get pending connections:', error);
        return [];
    }
}

/**
 * Clear pending connections
 */
export async function clearPendingConnections() {
    await AsyncStorage.removeItem(PENDING_CONNECTIONS_KEY);
}

/**
 * Manually trigger a connection check (useful for testing or pull-to-refresh)
 */
export async function manualCheckForConnections() {
    return checkForIncomingConnections();
}
