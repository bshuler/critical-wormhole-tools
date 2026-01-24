import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { BarCodeScanner } from 'expo-barcode-scanner';

export default function QRScannerScreen({ navigation }) {
    const [hasPermission, setHasPermission] = useState(null);
    const [scanned, setScanned] = useState(false);

    useEffect(() => {
        (async () => {
            const { status } = await BarCodeScanner.requestPermissionsAsync();
            setHasPermission(status === 'granted');
        })();
    }, []);

    const handleBarCodeScanned = ({ type, data }) => {
        setScanned(true);
        let code = data;

        // Handle wh:// protocol prefix
        if (data.startsWith('wh://')) {
            code = data.slice(5);
        }

        // Validate the code format (basic check for wormhole code pattern)
        const isValidCode = /^\d+-\w+(-\w+)?$/.test(code);

        if (isValidCode) {
            navigation.navigate('Connect', { scannedCode: code });
        } else {
            Alert.alert(
                'Invalid QR Code',
                'The scanned QR code does not contain a valid wormhole code.',
                [
                    { text: 'Scan Again', onPress: () => setScanned(false) },
                    { text: 'Cancel', onPress: () => navigation.goBack() }
                ]
            );
        }
    };

    if (hasPermission === null) {
        return (
            <View style={styles.container}>
                <Text style={styles.message}>Requesting camera permission...</Text>
            </View>
        );
    }

    if (hasPermission === false) {
        return (
            <View style={styles.container}>
                <Text style={styles.message}>No access to camera</Text>
                <Text style={styles.submessage}>
                    Camera permission is required to scan QR codes.
                </Text>
                <TouchableOpacity
                    style={styles.button}
                    onPress={() => navigation.goBack()}
                >
                    <Text style={styles.buttonText}>Go Back</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <BarCodeScanner
                onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
                style={styles.scanner}
                barCodeTypes={[BarCodeScanner.Constants.BarCodeType.qr]}
            />

            <View style={styles.overlay}>
                <View style={styles.overlayTop} />
                <View style={styles.overlayMiddle}>
                    <View style={styles.overlaySide} />
                    <View style={styles.scanArea}>
                        <View style={[styles.corner, styles.cornerTopLeft]} />
                        <View style={[styles.corner, styles.cornerTopRight]} />
                        <View style={[styles.corner, styles.cornerBottomLeft]} />
                        <View style={[styles.corner, styles.cornerBottomRight]} />
                    </View>
                    <View style={styles.overlaySide} />
                </View>
                <View style={styles.overlayBottom}>
                    <Text style={styles.instructionText}>
                        Point camera at a wormhole QR code
                    </Text>
                    {scanned && (
                        <TouchableOpacity
                            style={styles.rescanButton}
                            onPress={() => setScanned(false)}
                        >
                            <Text style={styles.rescanButtonText}>Tap to Scan Again</Text>
                        </TouchableOpacity>
                    )}
                    <TouchableOpacity
                        style={styles.cancelButton}
                        onPress={() => navigation.goBack()}
                    >
                        <Text style={styles.cancelButtonText}>Cancel</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#000',
        justifyContent: 'center',
        alignItems: 'center',
    },
    scanner: {
        ...StyleSheet.absoluteFillObject,
    },
    message: {
        fontSize: 18,
        color: '#fff',
        textAlign: 'center',
        marginBottom: 10,
    },
    submessage: {
        fontSize: 14,
        color: '#A0AEC0',
        textAlign: 'center',
        marginBottom: 20,
        paddingHorizontal: 40,
    },
    button: {
        backgroundColor: '#4299E1',
        paddingVertical: 12,
        paddingHorizontal: 30,
        borderRadius: 8,
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    overlay: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'center',
    },
    overlayTop: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
    },
    overlayMiddle: {
        flexDirection: 'row',
    },
    overlaySide: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
    },
    scanArea: {
        width: 250,
        height: 250,
        position: 'relative',
    },
    corner: {
        position: 'absolute',
        width: 30,
        height: 30,
        borderColor: '#4299E1',
    },
    cornerTopLeft: {
        top: 0,
        left: 0,
        borderTopWidth: 3,
        borderLeftWidth: 3,
    },
    cornerTopRight: {
        top: 0,
        right: 0,
        borderTopWidth: 3,
        borderRightWidth: 3,
    },
    cornerBottomLeft: {
        bottom: 0,
        left: 0,
        borderBottomWidth: 3,
        borderLeftWidth: 3,
    },
    cornerBottomRight: {
        bottom: 0,
        right: 0,
        borderBottomWidth: 3,
        borderRightWidth: 3,
    },
    overlayBottom: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        alignItems: 'center',
        paddingTop: 30,
    },
    instructionText: {
        color: '#fff',
        fontSize: 16,
        textAlign: 'center',
        marginBottom: 20,
    },
    rescanButton: {
        backgroundColor: '#4299E1',
        paddingVertical: 12,
        paddingHorizontal: 30,
        borderRadius: 8,
        marginBottom: 15,
    },
    rescanButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    cancelButton: {
        paddingVertical: 12,
        paddingHorizontal: 30,
    },
    cancelButtonText: {
        color: '#A0AEC0',
        fontSize: 16,
    },
});
