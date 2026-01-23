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

export default function BrowserScreen() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState(null);
  const [error, setError] = useState(null);

  const handleNavigate = async () => {
    if (!url.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setContent(null);

    try {
      // TODO: Implement WNS resolution and content fetching
      // const resolved = await wns.resolve(url);
      // const data = await wormhole.fetch(resolved);

      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Mock content
      setContent({
        title: `Content from ${url}`,
        body: 'This is placeholder content. Implement actual WNS resolution and content fetching.',
      });
    } catch (err) {
      setError(err.message || 'Failed to load content');
    } finally {
      setLoading(false);
    }
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
        </View>
      );
    }

    if (content) {
      return (
        <View style={styles.contentContainer}>
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
          Example: wh://example.tld
        </Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
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
  },
  placeholderText: {
    fontSize: 18,
    color: '#4A5568',
    marginBottom: 8,
  },
  exampleText: {
    fontSize: 14,
    color: '#A0AEC0',
    fontStyle: 'italic',
  },
  contentContainer: {
    padding: 20,
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
