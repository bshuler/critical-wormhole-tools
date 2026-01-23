import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';

export default function IdentitiesScreen() {
  const [identities, setIdentities] = useState([]);
  const [activeIdentity, setActiveIdentity] = useState(null);

  useEffect(() => {
    loadIdentities();
  }, []);

  const loadIdentities = async () => {
    // TODO: Load identities from secure storage
    // const stored = await SecureStore.getItemAsync('identities');

    // Mock data
    setIdentities([
      {
        id: '1',
        name: 'Default',
        publicKey: 'ed25519:abc123...',
        createdAt: new Date().toISOString(),
      },
    ]);
    setActiveIdentity('1');
  };

  const handleCreateIdentity = () => {
    Alert.prompt(
      'Create Identity',
      'Enter a name for the new identity',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Create',
          onPress: async (name) => {
            if (!name || !name.trim()) {
              return;
            }

            // TODO: Generate new keypair
            // const keypair = await crypto.generateKeyPair();
            // await SecureStore.setItemAsync(keypair.id, JSON.stringify(keypair));

            const newIdentity = {
              id: Date.now().toString(),
              name: name.trim(),
              publicKey: 'ed25519:' + Math.random().toString(36).substring(7),
              createdAt: new Date().toISOString(),
            };

            setIdentities([...identities, newIdentity]);
          },
        },
      ],
      'plain-text'
    );
  };

  const handleSelectIdentity = (id) => {
    setActiveIdentity(id);
    // TODO: Update active identity in global state/context
    Alert.alert('Identity Changed', `Active identity set to ${identities.find(i => i.id === id)?.name}`);
  };

  const handleDeleteIdentity = (id) => {
    const identity = identities.find(i => i.id === id);

    Alert.alert(
      'Delete Identity',
      `Are you sure you want to delete "${identity.name}"? This cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            // TODO: Delete from secure storage
            // await SecureStore.deleteItemAsync(id);

            setIdentities(identities.filter(i => i.id !== id));
            if (activeIdentity === id && identities.length > 1) {
              setActiveIdentity(identities.find(i => i.id !== id)?.id);
            }
          },
        },
      ]
    );
  };

  const handleExportIdentity = (id) => {
    // TODO: Export private key (with warning)
    Alert.alert(
      'Export Identity',
      'Exporting private keys is not yet implemented. This will allow you to back up and restore your identity.',
      [{ text: 'OK' }]
    );
  };

  const renderIdentity = ({ item }) => {
    const isActive = item.id === activeIdentity;

    return (
      <TouchableOpacity
        style={[styles.identityCard, isActive && styles.activeIdentityCard]}
        onPress={() => handleSelectIdentity(item.id)}
      >
        <View style={styles.identityHeader}>
          <Text style={styles.identityName}>{item.name}</Text>
          {isActive && (
            <View style={styles.activeBadge}>
              <Text style={styles.activeBadgeText}>Active</Text>
            </View>
          )}
        </View>

        <Text style={styles.publicKey} numberOfLines={1}>
          {item.publicKey}
        </Text>

        <Text style={styles.createdAt}>
          Created {new Date(item.createdAt).toLocaleDateString()}
        </Text>

        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => handleExportIdentity(item.id)}
          >
            <Text style={styles.actionButtonText}>Export</Text>
          </TouchableOpacity>

          {identities.length > 1 && (
            <TouchableOpacity
              style={[styles.actionButton, styles.deleteButton]}
              onPress={() => handleDeleteIdentity(item.id)}
            >
              <Text style={styles.deleteButtonText}>Delete</Text>
            </TouchableOpacity>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={identities}
        keyExtractor={(item) => item.id}
        renderItem={renderIdentity}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No identities found</Text>
        }
      />

      <TouchableOpacity
        style={styles.createButton}
        onPress={handleCreateIdentity}
      >
        <Text style={styles.createButtonText}>+ Create New Identity</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F7FAFC',
  },
  list: {
    padding: 16,
  },
  identityCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  activeIdentityCard: {
    borderColor: '#4299E1',
  },
  identityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  identityName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2D3748',
  },
  activeBadge: {
    backgroundColor: '#4299E1',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  activeBadgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  publicKey: {
    fontSize: 12,
    color: '#718096',
    fontFamily: 'monospace',
    marginBottom: 4,
  },
  createdAt: {
    fontSize: 12,
    color: '#A0AEC0',
    marginBottom: 12,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#EDF2F7',
    padding: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  actionButtonText: {
    color: '#4A5568',
    fontSize: 14,
    fontWeight: '600',
  },
  deleteButton: {
    backgroundColor: '#FED7D7',
  },
  deleteButtonText: {
    color: '#C53030',
    fontSize: 14,
    fontWeight: '600',
  },
  createButton: {
    backgroundColor: '#4299E1',
    margin: 16,
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyText: {
    textAlign: 'center',
    color: '#A0AEC0',
    fontSize: 16,
    marginTop: 40,
  },
});
