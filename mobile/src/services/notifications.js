import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

// Configure notification handler - how notifications appear when app is in foreground
Notifications.setNotificationHandler({
    handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
    }),
});

/**
 * Register for push notifications
 * Returns the Expo push token if successful
 */
export async function registerForPushNotifications() {
    let token;

    // Push notifications only work on physical devices
    if (!Device.isDevice) {
        console.log('Push notifications require a physical device');
        return null;
    }

    // Check existing permissions
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    // Request permission if not already granted
    if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
    }

    if (finalStatus !== 'granted') {
        console.log('Push notification permission not granted');
        return null;
    }

    // Get the Expo push token
    try {
        token = (await Notifications.getExpoPushTokenAsync({
            projectId: 'wormhole-mobile', // Replace with your Expo project ID
        })).data;
        console.log('Expo push token:', token);
    } catch (error) {
        console.error('Failed to get push token:', error);
        return null;
    }

    // Configure Android notification channel
    if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('wormhole-connections', {
            name: 'Wormhole Connections',
            importance: Notifications.AndroidImportance.HIGH,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#4299E1',
            sound: 'default',
        });
    }

    return token;
}

/**
 * Send a local notification immediately
 */
export async function sendLocalNotification(title, body, data = {}) {
    await Notifications.scheduleNotificationAsync({
        content: {
            title,
            body,
            data,
            sound: 'default',
            priority: Notifications.AndroidNotificationPriority.HIGH,
        },
        trigger: null, // null means send immediately
    });
}

/**
 * Schedule a notification for later
 */
export async function scheduleNotification(title, body, seconds, data = {}) {
    const id = await Notifications.scheduleNotificationAsync({
        content: {
            title,
            body,
            data,
            sound: 'default',
        },
        trigger: {
            seconds,
        },
    });
    return id;
}

/**
 * Cancel a scheduled notification
 */
export async function cancelNotification(notificationId) {
    await Notifications.cancelScheduledNotificationAsync(notificationId);
}

/**
 * Cancel all scheduled notifications
 */
export async function cancelAllNotifications() {
    await Notifications.cancelAllScheduledNotificationsAsync();
}

/**
 * Notify user of an incoming wormhole connection
 */
export function notifyIncomingConnection(code, peerInfo = {}) {
    const peerName = peerInfo.name || 'A peer';
    sendLocalNotification(
        'Incoming Wormhole Connection',
        `${peerName} is requesting connection with code: ${code}`,
        {
            type: 'incoming_connection',
            code,
            peerInfo,
        }
    );
}

/**
 * Notify user of successful connection
 */
export function notifyConnectionEstablished(code, peerInfo = {}) {
    const peerName = peerInfo.name || 'Peer';
    sendLocalNotification(
        'Connected!',
        `Successfully connected to ${peerName}`,
        {
            type: 'connection_established',
            code,
            peerInfo,
        }
    );
}

/**
 * Notify user of connection failure
 */
export function notifyConnectionFailed(code, reason = 'Unknown error') {
    sendLocalNotification(
        'Connection Failed',
        `Failed to connect with code ${code}: ${reason}`,
        {
            type: 'connection_failed',
            code,
            reason,
        }
    );
}

/**
 * Notify user of incoming file transfer
 */
export function notifyFileTransfer(fileName, fileSize, peerInfo = {}) {
    const peerName = peerInfo.name || 'A peer';
    const sizeStr = formatFileSize(fileSize);
    sendLocalNotification(
        'Incoming File',
        `${peerName} wants to send you "${fileName}" (${sizeStr})`,
        {
            type: 'file_transfer',
            fileName,
            fileSize,
            peerInfo,
        }
    );
}

/**
 * Add a listener for notification responses (when user taps notification)
 */
export function addNotificationResponseListener(callback) {
    return Notifications.addNotificationResponseReceivedListener(callback);
}

/**
 * Add a listener for incoming notifications (when notification is received)
 */
export function addNotificationReceivedListener(callback) {
    return Notifications.addNotificationReceivedListener(callback);
}

/**
 * Get the last notification that opened the app
 */
export async function getLastNotificationResponse() {
    return Notifications.getLastNotificationResponseAsync();
}

/**
 * Helper to format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
