import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useWormhole } from '../hooks/useWormhole';

export default function BrowserScreen() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState(null);
  const [error, setError] = useState(null);

  const { connections, isConnected } = useWormhole();

  const handleNavigate = async () => {
    if (!url.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setContent(null);

    try {
      // Parse the WNS URL
      // Format: wh://domain.tld/path or wormhole://code/path
      const parsed = parseWnsUrl(url);

      if (parsed.type === 'direct' && !isConnected) {
        throw new Error('No active wormhole connection. Connect to a peer first.');
      }

      // TODO: Implement WNS resolution and content fetching
      // For direct wormhole URLs, use the active connection
      // For WNS URLs, resolve the name first then fetch

      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Mock content based on URL type
      if (parsed.type === 'wns') {
        setContent({
          title: `WNS: ${parsed.domain}`,
          body: `This is placeholder content for the WNS domain "${parsed.domain}".\n\nPath: ${parsed.path || '/'}\n\nWNS resolution would look up this domain in the decentralized naming system and route to the appropriate peer.`,
          type: 'wns',
        });
      } else {
        setContent({
          title: `Direct Connection`,
          body: `Connected to peer via wormhole.\n\nPath: ${parsed.path || '/'}\n\nIn a full implementation, this would fetch content directly from the connected peer.`,
          type: 'direct',
        });
      }
    } catch (err) {
      setError(err.message || 'Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  const parseWnsUrl = (input) => {
    const trimmed = input.trim().toLowerCase();

    // wh://domain.tld/path format (WNS lookup)
    if (trimmed.startsWith('wh://')) {
      const rest = trimmed.slice(5);
      const slashIndex = rest.indexOf('/');
      if (slashIndex === -1) {
        return { type: 'wns', domain: rest, path: '/' };
      }
      return {
        type: 'wns',
        domain: rest.slice(0, slashIndex),
        path: rest.slice(slashIndex),
      };
    }

    // wormhole://code/path format (direct connection)
    if (trimmed.startsWith('wormhole://')) {
      const rest = trimmed.slice(11);
      const slashIndex = rest.indexOf('/');
      if (slashIndex === -1) {
        return { type: 'direct', code: rest, path: '/' };
      }
      return {
        type: 'direct',
        code: rest.slice(0, slashIndex),
        path: rest.slice(slashIndex),
      };
    }

    // Assume WNS if no protocol
    const slashIndex = trimmed.indexOf('/');
    if (slashIndex === -1) {
      return { type: 'wns', domain: trimmed, path: '/' };
    }
    return {
      type: 'wns',
      domain: trimmed.slice(0, slashIndex),
      path: trimmed.slice(slashIndex),
    };
  };

  const renderContent = () => {
    if (loading) {
      return (
        <View style={styles.centerContent}>
          <ActivityIndicator size="large" color="#4299E1" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      );
    }

    if (error) {
      return (
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={handleNavigate}
          >
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      );
    }

    if (content) {
      return (
        <View style={styles.contentContainer}>
          <View style={styles.contentHeader}>
            <Text style={styles.contentType}>
              {content.type === 'wns' ? 'WNS' : 'Direct'}
            </Text>
          </View>
          <Text style={styles.contentTitle}>{content.title}</Text>
          <Text style={styles.contentBody}>{content.body}</Text>
        </View>
      );
    }

    return (
      <View style={styles.centerContent}>
        <Text style={styles.placeholderText}>
          Enter a WNS URL to browse
        </Text>
        <Text style={styles.exampleText}>
          Examples:
        </Text>
        <Text style={styles.exampleUrl}>wh://example.tld</Text>
        <Text style={styles.exampleUrl}>wormhole://7-correct-horse/path</Text>

        {!isConnected && (
          <View style={styles.warningBox}>
            <Text style={styles.warningText}>
              No active connections. Connect to a peer on the Connect tab to browse direct wormhole URLs.
            </Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Connection Status Bar */}
      <View style={[
        styles.statusBar,
        isConnected ? styles.statusConnected : styles.statusDisconnected
      ]}>
        <Text style={styles.statusText}>
          {isConnected
            ? `Connected (${connections.length} peer${connections.length > 1 ? 's' : ''})`
            : 'Not connected'}
        </Text>
      </View>

      <View style={styles.addressBar}>
        <TextInput
          style={styles.urlInput}
          placeholder="wh://example.tld"
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          onSubmitEditing={handleNavigate}
        />
        <TouchableOpacity
          style={styles.goButton}
          onPress={handleNavigate}
          disabled={loading}
        >
          <Text style={styles.goButtonText}>Go</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.contentArea}>
        {renderContent()}
      </ScrollView>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          WNS Browser - Decentralized naming system
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F7FAFC',
  },
  statusBar: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    alignItems: 'center',
  },
  statusConnected: {
    backgroundColor: '#C6F6D5',
  },
  statusDisconnected: {
    backgroundColor: '#FED7D7',
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#2D3748',
  },
  addressBar: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  urlInput: {
    flex: 1,
    backgroundColor: '#EDF2F7',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginRight: 8,
  },
  goButton: {
    backgroundColor: '#4299E1',
    borderRadius: 8,
    paddingHorizontal: 20,
    justifyContent: 'center',
  },
  goButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  contentArea: {
    flex: 1,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    minHeight: 400,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#718096',
  },
  errorText: {
    fontSize: 16,
    color: '#E53E3E',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#4299E1',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  placeholderText: {
    fontSize: 18,
    color: '#4A5568',
    marginBottom: 16,
  },
  exampleText: {
    fontSize: 14,
    color: '#718096',
    marginBottom: 8,
  },
  exampleUrl: {
    fontSize: 14,
    color: '#4299E1',
    fontFamily: 'monospace',
    marginBottom: 4,
  },
  warningBox: {
    marginTop: 24,
    backgroundColor: '#FEFCBF',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ECC94B',
  },
  warningText: {
    fontSize: 14,
    color: '#744210',
    textAlign: 'center',
  },
  contentContainer: {
    padding: 20,
  },
  contentHeader: {
    marginBottom: 8,
  },
  contentType: {
    fontSize: 12,
    fontWeight: '600',
    color: '#718096',
    textTransform: 'uppercase',
    backgroundColor: '#EDF2F7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  contentTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2D3748',
    marginBottom: 16,
  },
  contentBody: {
    fontSize: 16,
    color: '#4A5568',
    lineHeight: 24,
  },
  footer: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    padding: 12,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#A0AEC0',
  },
});
