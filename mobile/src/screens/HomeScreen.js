import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';

export default function HomeScreen({ navigation }) {
  const [code, setCode] = useState('');
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    if (!code.trim()) {
      Alert.alert('Error', 'Please enter a wormhole code');
      return;
    }

    setConnecting(true);
    try {
      // TODO: Implement wormhole connection logic
      // const connection = await wormhole.connect(code);

      // Simulate connection delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      Alert.alert('Success', `Connected to peer with code: ${code}`);
      setCode('');
    } catch (error) {
      Alert.alert('Connection Failed', error.message);
    } finally {
      setConnecting(false);
    }
  };

  const handleScanQR = () => {
    // TODO: Navigate to QR scanner
    Alert.alert('QR Scanner', 'QR scanning not yet implemented');
  };

  const handleGenerateCode = () => {
    // TODO: Generate wormhole code for receiving connections
    const generatedCode = `${Math.floor(Math.random() * 99)}-wormhole-word`;
    Alert.alert('Your Wormhole Code', generatedCode, [
      { text: 'Copy', onPress: () => {} },
      { text: 'Show QR', onPress: () => {} },
      { text: 'Close' },
    ]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Connect to Peer</Text>

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

      <TouchableOpacity
        style={styles.browserButton}
        onPress={() => navigation.navigate('Browser')}
        disabled={connecting}
      >
        <Text style={styles.browserButtonText}>Open WNS Browser →</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F7FAFC',
    justifyContent: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 30,
    textAlign: 'center',
    color: '#2D3748',
  },
  inputContainer: {
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E0',
    borderRadius: 8,
    padding: 15,
    fontSize: 16,
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
  browserButton: {
    marginTop: 10,
    padding: 12,
    alignItems: 'center',
  },
  browserButtonText: {
    color: '#718096',
    fontSize: 14,
  },
});
