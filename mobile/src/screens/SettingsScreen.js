import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Alert,
} from 'react-native';

export default function SettingsScreen() {
  const [relayUrl, setRelayUrl] = useState('');
  const [dhtEnabled, setDhtEnabled] = useState(true);
  const [autoConnect, setAutoConnect] = useState(false);
  const [debugMode, setDebugMode] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    // TODO: Load settings from AsyncStorage
    // const settings = await AsyncStorage.getItem('settings');

    // Mock default settings
    setRelayUrl('wss://relay.magic-wormhole.io:4000');
    setDhtEnabled(true);
    setAutoConnect(false);
    setDebugMode(false);
  };

  const handleSaveSettings = async () => {
    try {
      // TODO: Validate and save settings
      // await AsyncStorage.setItem('settings', JSON.stringify({
      //   relayUrl,
      //   dhtEnabled,
      //   autoConnect,
      //   debugMode,
      // }));

      Alert.alert('Success', 'Settings saved successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const handleResetSettings = () => {
    Alert.alert(
      'Reset Settings',
      'Are you sure you want to reset all settings to defaults?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            setRelayUrl('wss://relay.magic-wormhole.io:4000');
            setDhtEnabled(true);
            setAutoConnect(false);
            setDebugMode(false);
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Network</Text>

        <View style={styles.setting}>
          <Text style={styles.label}>Relay Server URL</Text>
          <TextInput
            style={styles.input}
            value={relayUrl}
            onChangeText={setRelayUrl}
            placeholder="wss://relay.example.com:4000"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
          <Text style={styles.hint}>
            WebSocket URL for the magic-wormhole relay server
          </Text>
        </View>

        <View style={styles.setting}>
          <View style={styles.switchRow}>
            <View style={styles.switchLabel}>
              <Text style={styles.label}>Enable DHT</Text>
              <Text style={styles.hint}>
                Use distributed hash table for peer discovery
              </Text>
            </View>
            <Switch
              value={dhtEnabled}
              onValueChange={setDhtEnabled}
              trackColor={{ false: '#CBD5E0', true: '#63B3ED' }}
              thumbColor={dhtEnabled ? '#4299E1' : '#E2E8F0'}
            />
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection</Text>

        <View style={styles.setting}>
          <View style={styles.switchRow}>
            <View style={styles.switchLabel}>
              <Text style={styles.label}>Auto-Connect</Text>
              <Text style={styles.hint}>
                Automatically accept incoming connections
              </Text>
            </View>
            <Switch
              value={autoConnect}
              onValueChange={setAutoConnect}
              trackColor={{ false: '#CBD5E0', true: '#63B3ED' }}
              thumbColor={autoConnect ? '#4299E1' : '#E2E8F0'}
            />
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Advanced</Text>

        <View style={styles.setting}>
          <View style={styles.switchRow}>
            <View style={styles.switchLabel}>
              <Text style={styles.label}>Debug Mode</Text>
              <Text style={styles.hint}>
                Show detailed logs and diagnostic information
              </Text>
            </View>
            <Switch
              value={debugMode}
              onValueChange={setDebugMode}
              trackColor={{ false: '#CBD5E0', true: '#63B3ED' }}
              thumbColor={debugMode ? '#4299E1' : '#E2E8F0'}
            />
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Version</Text>
          <Text style={styles.infoValue}>0.1.0</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Protocol</Text>
          <Text style={styles.infoValue}>Magic Wormhole</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>License</Text>
          <Text style={styles.infoValue}>MIT</Text>
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={handleSaveSettings}
        >
          <Text style={styles.buttonText}>Save Settings</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.secondaryButton]}
          onPress={handleResetSettings}
        >
          <Text style={styles.buttonTextSecondary}>Reset to Defaults</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F7FAFC',
  },
  section: {
    backgroundColor: '#fff',
    marginTop: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#718096',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  setting: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    color: '#2D3748',
    marginBottom: 4,
  },
  hint: {
    fontSize: 13,
    color: '#A0AEC0',
    marginTop: 4,
  },
  input: {
    backgroundColor: '#EDF2F7',
    borderRadius: 6,
    padding: 12,
    fontSize: 14,
    marginTop: 8,
    fontFamily: 'monospace',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  switchLabel: {
    flex: 1,
    marginRight: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  infoLabel: {
    fontSize: 16,
    color: '#4A5568',
  },
  infoValue: {
    fontSize: 16,
    color: '#2D3748',
    fontWeight: '500',
  },
  actions: {
    padding: 16,
    paddingBottom: 32,
  },
  button: {
    padding: 16,
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
    borderColor: '#CBD5E0',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonTextSecondary: {
    color: '#4A5568',
    fontSize: 16,
    fontWeight: '600',
  },
});
