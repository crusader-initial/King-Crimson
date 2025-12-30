import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { uploadDocument } from '../src/services/api';
import { router } from 'expo-router';

export default function UploadScreen() {
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['text/plain', 'text/markdown'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled) {
        setSelectedFile(result.assets[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setLoading(true);
    try {
      await uploadDocument(selectedFile);
      Alert.alert('Success', 'Character knowledge uploaded successfully!', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } catch (error) {
      Alert.alert('Error', 'Failed to upload document');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.label}>Select Knowledge Source</Text>
        <Text style={styles.description}>
          Upload a text file or markdown document containing information about the character you want to create.
        </Text>

        <TouchableOpacity style={styles.uploadBox} onPress={pickDocument}>
          <Text style={styles.uploadText}>
            {selectedFile ? selectedFile.name : 'Tap to select file'}
          </Text>
        </TouchableOpacity>

        {selectedFile && (
          <TouchableOpacity 
            style={[styles.button, loading && styles.disabledButton]} 
            onPress={handleUpload}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Start Ingestion</Text>
            )}
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#FFE5F0',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 15,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  label: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
    lineHeight: 20,
  },
  uploadBox: {
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    borderRadius: 10,
    padding: 30,
    alignItems: 'center',
    marginBottom: 20,
    backgroundColor: '#fafafa',
  },
  uploadText: {
    color: '#FF6B9D',
    fontSize: 16,
    fontWeight: '500',
  },
  button: {
    backgroundColor: '#B6D9FF',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
