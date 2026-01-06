import { View, Text, StyleSheet, TextInput, TouchableOpacity, StatusBar, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { useState } from 'react';
import { updateRoleName } from '../src/services/api';
import { useUser } from '../src/contexts/UserContext';

export default function NameInputScreen() {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { userId, userInfo, updateUserInfo } = useUser();

  const handleNext = async () => {
    if (!name.trim() || loading) return;
    
    if (!userId) {
      Alert.alert('错误', '未找到用户ID，请重新登录');
      router.replace('/login');
      return;
    }

    setLoading(true);
    try {
      // 更新角色名称（只更新roles.name，不更新loads.name）
      const response = await updateRoleName(userId, name.trim());
      if (response.code === 200) {
        // 直接更新本地用户信息的 name 字段
        if (userInfo) {
          await updateUserInfo({
            ...userInfo,
            name: name.trim()
          });
        }
        
        // 更新成功，跳转到信息采集页面
        router.replace('/info-collection');
      } else {
        Alert.alert('错误', response.message || '更新角色名称失败');
      }
    } catch (error) {
      console.error('Update role name error:', error);
      const errorMessage = error?.response?.data?.message || '网络请求失败，请检查网络连接';
      Alert.alert('错误', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={['#FFE5F0', '#E5F0FF', '#D6E8FF']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="dark-content" />
      
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
      >
        {/* 标题文字区域 */}
        <View style={styles.titleContainer}>
          <Text style={styles.titleText}>给“我”起个名字吧！</Text>
        </View>

        {/* 输入框区域 */}
        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            placeholder="输入昵称"
            placeholderTextColor="rgba(0, 0, 0, 0.4)"
            value={name}
            onChangeText={setName}
            autoFocus={true}
          />
        </View>

        {/* 下一步按钮 */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity 
            style={[
              styles.nextButton,
              (!name.trim() || loading) && styles.nextButtonDisabled,
            ]}
            onPress={handleNext}
            activeOpacity={0.8}
            disabled={!name.trim() || loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#FF6B9D" />
            ) : (
              <Text style={styles.buttonText}>下一步</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 30,
    paddingTop: 100,
    paddingBottom: 40,
  },
  titleContainer: {
    alignItems: 'center',
    marginBottom: 60,
  },
  titleText: {
    fontSize: 24,
    color: '#333333',
    fontWeight: '600',
    textAlign: 'center',
  },
  inputWrapper: {
    width: '100%',
    marginBottom: 40,
  },
  input: {
    width: '100%',
    height: 50,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 16,
    color: '#333333',
    fontSize: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  buttonContainer: {
    width: '100%',
  },
  nextButton: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextButtonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#FF6B9D',
    fontSize: 16,
    fontWeight: '600',
  },
});

