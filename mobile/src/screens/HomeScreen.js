import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
} from 'react-native';
import { useWormhole, useConnectionHistory } from '../hooks/useWormhole';
import QRCodeDisplay from '../components/QRCodeDisplay';
import { addActiveCode, removeActiveCode } from '../services/backgroundListener';

export default function HomeScreen({ navigation, route }) {
  const [code, setCode] = useState('');
  const [generatedCode, setGeneratedCode] = useState(null);
  const [showQRModal, setShowQRModal] = useState(false);
  const {
    connections,
    connecting,
    error,
    connect,
    disconnect,
    generateCode,
    clearError,
  } = useWormhole();
  const { history } = useConnectionHistory();

  // Handle scanned QR code from QRScannerScreen
  useEffect(() => {
    if (route.params?.scannedCode) {
      setCode(route.params.scannedCode);
      // Clear the param to prevent re-setting on future navigations
      navigation.setParams({ scannedCode: undefined });
    }
  }, [route.params?.scannedCode, navigation]);

  const handleConnect = async () => {
    if (!code.trim()) {
      Alert.alert('Error', 'Please enter a wormhole code');
      return;
    }

    try {
      await connect(code);
      Alert.alert('Success', `Connected to peer with code: ${code}`);
      setCode('');
    } catch (err) {
      Alert.alert('Connection Failed', err.message);
    }
  };

  const handleScanQR = () => {
    navigation.navigate('QRScanner');
  };

  const handleGenerateCode = async () => {
    const newCode = generateCode();
    setGeneratedCode(newCode);

    // Register the code for background listening
    await addActiveCode(newCode, { purpose: 'receive' });

    Alert.alert('Your Wormhole Code', newCode, [
      {
        text: 'Show QR',
        onPress: () => setShowQRModal(true),
      },
      { text: 'Copy', onPress: () => {} },
      { text: 'Close' },
    ]);
  };

  const handleCloseQRModal = async () => {
    setShowQRModal(false);
    // Ask if user wants to stop listening for this code
    if (generatedCode) {
      Alert.alert(
        'Keep Listening?',
        'Do you want to keep listening for connections with this code in the background?',
        [
          {
            text: 'Yes, Keep Listening',
            onPress: () => {},
          },
          {
            text: 'No, Stop',
            style: 'cancel',
            onPress: () => {
              removeActiveCode(generatedCode);
              setGeneratedCode(null);
            },
          },
        ]
      );
    }
  };

  const handleDisconnect = (connectionCode) => {
    Alert.alert(
      'Disconnect',
      `Disconnect from ${connectionCode}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: () => disconnect(connectionCode),
        },
      ]
    );
  };

  const handleHistoryItemPress = (item) => {
    setCode(item.code);
  };

  const renderConnection = ({ item }) => (
    <TouchableOpacity
      style={styles.connectionItem}
      onPress={() => handleDisconnect(item.code)}
    >
      <View style={styles.connectionInfo}>
        <Text style={styles.connectionCode}>{item.code}</Text>
        <Text style={styles.connectionStatus}>Connected</Text>
      </View>
      <Text style={styles.disconnectText}>Tap to disconnect</Text>
    </TouchableOpacity>
  );

  const renderHistoryItem = ({ item }) => (
    <TouchableOpacity
      style={styles.historyItem}
      onPress={() => handleHistoryItemPress(item)}
    >
      <Text style={styles.historyCode}>{item.code}</Text>
      <Text style={styles.historyDate}>
        {new Date(item.timestamp).toLocaleDateString()}
      </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Connect to Peer</Text>

      {/* Active Connections */}
      {connections.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Active Connections</Text>
          <FlatList
            data={connections}
            renderItem={renderConnection}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
          />
        </View>
      )}

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Enter wormhole code (e.g., 7-correct-horse)"
          value={code}
          onChangeText={setCode}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!connecting}
        />
      </View>

      {error && (
        <TouchableOpacity onPress={clearError}>
          <Text style={styles.errorText}>{error} (tap to dismiss)</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity
        style={[styles.button, styles.primaryButton]}
        onPress={handleConnect}
        disabled={connecting}
      >
        {connecting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Connect</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.button, styles.secondaryButton]}
        onPress={handleScanQR}
        disabled={connecting}
      >
        <Text style={styles.buttonTextSecondary}>Scan QR Code</Text>
      </TouchableOpacity>

      <View style={styles.divider} />

      <TouchableOpacity
        style={[styles.button, styles.secondaryButton]}
        onPress={handleGenerateCode}
        disabled={connecting}
      >
        <Text style={styles.buttonTextSecondary}>Generate Code to Receive</Text>
      </TouchableOpacity>

      {/* Show active code if generated */}
      {generatedCode && (
        <TouchableOpacity
          style={styles.activeCodeContainer}
          onPress={() => setShowQRModal(true)}
        >
          <Text style={styles.activeCodeLabel}>Active Code (tap to show QR)</Text>
          <Text style={styles.activeCodeText}>{generatedCode}</Text>
        </TouchableOpacity>
      )}

      {/* Recent Connections */}
      {history.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Connections</Text>
          <FlatList
            data={history.slice(0, 5)}
            renderItem={renderHistoryItem}
            keyExtractor={(item, index) => `${item.code}-${index}`}
            scrollEnabled={false}
          />
        </View>
      )}

      <TouchableOpacity
        style={styles.browserButton}
        onPress={() => navigation.navigate('Browser')}
        disabled={connecting}
      >
        <Text style={styles.browserButtonText}>Open WNS Browser</Text>
      </TouchableOpacity>

      {/* QR Code Modal */}
      <Modal
        visible={showQRModal}
        animationType="fade"
        transparent={true}
        onRequestClose={handleCloseQRModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Scan to Connect</Text>
            {generatedCode && (
              <QRCodeDisplay
                code={generatedCode}
                size={220}
                showCode={true}
                showActions={true}
                onClose={handleCloseQRModal}
              />
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F7FAFC',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#2D3748',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#718096',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  connectionItem: {
    backgroundColor: '#C6F6D5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  connectionInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  connectionCode: {
    fontSize: 16,
    fontWeight: '600',
    color: '#276749',
  },
  connectionStatus: {
    fontSize: 12,
    color: '#38A169',
  },
  disconnectText: {
    fontSize: 11,
    color: '#276749',
    marginTop: 4,
  },
  historyItem: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  historyCode: {
    fontSize: 14,
    color: '#4A5568',
  },
  historyDate: {
    fontSize: 12,
    color: '#A0AEC0',
  },
  inputContainer: {
    marginBottom: 12,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E0',
    borderRadius: 8,
    padding: 15,
    fontSize: 16,
  },
  errorText: {
    color: '#E53E3E',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  button: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#4299E1',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#4299E1',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonTextSecondary: {
    color: '#4299E1',
    fontSize: 16,
    fontWeight: '600',
  },
  divider: {
    height: 1,
    backgroundColor: '#E2E8F0',
    marginVertical: 20,
  },
  activeCodeContainer: {
    backgroundColor: '#EBF8FF',
    borderRadius: 8,
    padding: 15,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#4299E1',
    alignItems: 'center',
  },
  activeCodeLabel: {
    fontSize: 12,
    color: '#4299E1',
    marginBottom: 5,
  },
  activeCodeText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2D3748',
    fontFamily: 'monospace',
  },
  browserButton: {
    marginTop: 10,
    padding: 12,
    alignItems: 'center',
  },
  browserButtonText: {
    color: '#718096',
    fontSize: 14,
  },
  modalOverlay: {
    flex: 1,
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
