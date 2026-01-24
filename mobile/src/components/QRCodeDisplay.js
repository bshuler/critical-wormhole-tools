import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Share, Clipboard } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

/**
 * QRCodeDisplay - Displays a QR code for sharing wormhole codes
 *
 * @param {string} code - The wormhole code to encode
 * @param {number} size - Size of the QR code (default: 200)
 * @param {boolean} showCode - Whether to display the code text below (default: true)
 * @param {boolean} showActions - Whether to show share/copy buttons (default: true)
 * @param {function} onClose - Callback when close is pressed (optional)
 */
export default function QRCodeDisplay({
    code,
    size = 200,
    showCode = true,
    showActions = true,
    onClose,
}) {
    // Format code with wh:// prefix for QR encoding
    const qrValue = `wh://${code}`;

    const handleCopy = async () => {
        try {
            await Clipboard.setString(code);
            // Note: In a real app, you'd want to show a toast notification
        } catch (error) {
            console.error('Failed to copy code:', error);
        }
    };

    const handleShare = async () => {
        try {
            await Share.share({
                message: `Connect to me via Wormhole: ${code}`,
                title: 'Wormhole Connection Code',
            });
        } catch (error) {
            console.error('Failed to share code:', error);
        }
    };

    return (
        <View style={styles.container}>
            <View style={styles.qrContainer}>
                <QRCode
                    value={qrValue}
                    size={size}
                    color="#2D3748"
                    backgroundColor="#fff"
                    logo={null}
                    logoSize={30}
                    logoBackgroundColor="#fff"
                    logoMargin={2}
                    logoBorderRadius={5}
                    quietZone={10}
                    enableLinearGradient={false}
                />
            </View>

            {showCode && (
                <View style={styles.codeContainer}>
                    <Text style={styles.codeLabel}>Your Wormhole Code</Text>
                    <Text style={styles.codeText}>{code}</Text>
                </View>
            )}

            {showActions && (
                <View style={styles.actionsContainer}>
                    <TouchableOpacity style={styles.actionButton} onPress={handleCopy}>
                        <Text style={styles.actionButtonText}>Copy Code</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
                        <Text style={styles.actionButtonText}>Share</Text>
                    </TouchableOpacity>
                </View>
            )}

            {onClose && (
                <TouchableOpacity style={styles.closeButton} onPress={onClose}>
                    <Text style={styles.closeButtonText}>Close</Text>
                </TouchableOpacity>
            )}
        </View>
    );
}

/**
 * QRCodeModal - Full screen modal for displaying QR codes
 */
export function QRCodeModal({ visible, code, onClose }) {
    if (!visible) return null;

    return (
        <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
                <Text style={styles.modalTitle}>Scan to Connect</Text>
                <QRCodeDisplay
                    code={code}
                    size={250}
                    showCode={true}
                    showActions={true}
                    onClose={onClose}
                />
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        alignItems: 'center',
        padding: 20,
    },
    qrContainer: {
        backgroundColor: '#fff',
        padding: 15,
        borderRadius: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    codeContainer: {
        marginTop: 20,
        alignItems: 'center',
    },
    codeLabel: {
        fontSize: 14,
        color: '#718096',
        marginBottom: 5,
    },
    codeText: {
        fontSize: 20,
        fontWeight: '600',
        color: '#2D3748',
        fontFamily: 'monospace',
    },
    actionsContainer: {
        flexDirection: 'row',
        marginTop: 20,
        gap: 12,
    },
    actionButton: {
        backgroundColor: '#4299E1',
        paddingVertical: 10,
        paddingHorizontal: 20,
        borderRadius: 8,
    },
    actionButtonText: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    closeButton: {
        marginTop: 20,
        paddingVertical: 10,
        paddingHorizontal: 30,
    },
    closeButtonText: {
        color: '#718096',
        fontSize: 16,
    },
    modalOverlay: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    modalContent: {
        backgroundColor: '#F7FAFC',
        borderRadius: 16,
        padding: 25,
        alignItems: 'center',
        maxWidth: 350,
        width: '90%',
    },
    modalTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#2D3748',
        marginBottom: 15,
    },
});
