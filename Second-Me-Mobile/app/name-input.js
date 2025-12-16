import { View, Text, StyleSheet, TextInput, TouchableOpacity, StatusBar, ActivityIndicator, Alert } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { useState } from 'react';
import { createUser } from '../src/services/api';

export default function NameInputScreen() {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleNext = async () => {
    if (!name.trim() || loading) return;

    setLoading(true);
    try {
      const response = await createUser(name.trim());
      if (response.code === 200) {
        // 创建成功，跳转到信息采集页面
        router.push('/info-collection');
      } else {
        Alert.alert('错误', response.message || '创建用户失败');
      }
    } catch (error) {
      console.error('Create user error:', error);
      Alert.alert('错误', '网络请求失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={['#E8D5FF', '#9B7EDE', '#6B4FA0']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="light-content" />
      
      {/* 笑脸图标 */}
      <View style={styles.iconContainer}>
        <View style={styles.smileyIcon}>
          <Text style={styles.smileyEyes}>{'>'}</Text>
          <Text style={styles.smileyEyes}>{'>'}</Text>
          <Text style={styles.smileyMouth}>)</Text>
        </View>
      </View>

      {/* 标题文字 */}
      <Text style={styles.titleText}>"我"的名字叫什么</Text>

      {/* 输入框 */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="输入你的名字"
          placeholderTextColor="rgba(255, 255, 255, 0.6)"
          value={name}
          onChangeText={setName}
          autoFocus={true}
        />
      </View>

      {/* 下一步按钮 */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={styles.nextButton}
          onPress={handleNext}
          activeOpacity={0.8}
          disabled={!name.trim() || loading}
        >
          <LinearGradient
            colors={['#FFB6C1', '#FFA07A']}
            style={styles.buttonGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <>
                <Text style={styles.buttonText}>下一步</Text>
                <Text style={styles.buttonArrow}>{'>'}</Text>
              </>
            )}
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 60,
    paddingHorizontal: 30,
    paddingBottom: 40,
  },
  iconContainer: {
    marginBottom: 40,
    marginTop: 60,
  },
  smileyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    paddingTop: 10,
  },
  smileyEyes: {
    fontSize: 16,
    color: '#000000',
    marginHorizontal: 8,
  },
  smileyMouth: {
    fontSize: 20,
    color: '#000000',
    marginLeft: 4,
  },
  titleText: {
    fontSize: 22,
    color: '#FFFFFF',
    fontWeight: '500',
    marginBottom: 50,
    textAlign: 'center',
  },
  inputContainer: {
    width: '100%',
    marginBottom: 40,
  },
  input: {
    width: '100%',
    height: 50,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 25,
    paddingHorizontal: 20,
    color: '#FFFFFF',
    fontSize: 18,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  buttonContainer: {
    position: 'absolute',
    bottom: 40,
    left: 30,
    right: 30,
  },
  nextButton: {
    width: '100%',
    borderRadius: 30,
    overflow: 'hidden',
  },
  buttonGradient: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 18,
    paddingHorizontal: 30,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
    marginRight: 8,
  },
  buttonArrow: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
  },
});

