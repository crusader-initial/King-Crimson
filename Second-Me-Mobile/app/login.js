import { useState, useRef } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TextInput, 
  TouchableOpacity, 
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { loginOrCreateUser } from '../src/services/api';
import { useUser } from '../src/contexts/UserContext';

export default function LoginScreen() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const codeInputRef = useRef(null);
  const { login } = useUser();

  // 验证码倒计时
  const startCountdown = () => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // 获取验证码（仅前端样式）
  const handleGetCode = () => {
    // 验证手机号格式
    if (!phoneNumber.trim()) {
      Alert.alert('提示', '请输入手机号');
      return;
    }
    
    // 简单的手机号格式验证（11位数字）
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(phoneNumber.trim())) {
      Alert.alert('提示', '请输入正确的手机号');
      return;
    }

    // 开始倒计时
    startCountdown();
    
    // 聚焦到验证码输入框
    setTimeout(() => {
      codeInputRef.current?.focus();
    }, 300);
  };

  // 处理登录
  const handleLogin = async () => {
    // 验证手机号
    if (!phoneNumber.trim()) {
      Alert.alert('提示', '请输入手机号');
      return;
    }

    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(phoneNumber.trim())) {
      Alert.alert('提示', '请输入正确的手机号');
      return;
    }

    // 验证验证码（任何六位数都可以）
    if (!verificationCode.trim()) {
      Alert.alert('提示', '请输入验证码');
      return;
    }

    if (!/^\d{6}$/.test(verificationCode.trim())) {
      Alert.alert('提示', '验证码必须是6位数字');
      return;
    }

    setLoading(true);

    try {
      // 调用登录或创建用户接口（根据手机号）
      const response = await loginOrCreateUser(phoneNumber.trim());
      
      if (response && response.code === 200 && response.data) {
        const userId = response.data.id;
        const userInfo = {
          id: userId,
          user_mobile: response.data.user_mobile,
          name: response.data.name
        };
        
        // 保存用户ID和信息到Context和AsyncStorage
        await login(userId, userInfo);
        
        // 判断是新用户还是已存在用户
        const isNewUser = response.data.is_new_user;
        
        if (isNewUser) {
          // 新用户：跳转到输入用户名界面
          router.replace('/name-input');
        } else {
          // 已存在用户：直接跳转到主界面
          router.replace('/home');
        }
      } else {
        Alert.alert('错误', response?.message || '登录失败');
      }
    } catch (error) {
      console.error('登录失败:', error);
      const errorMessage = error?.response?.data?.message || '网络连接失败，请稍后再试';
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
        style={styles.content}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={100}
      >
        {/* 标题区域 */}
        <View style={styles.header}>
          <Text style={styles.title}>欢迎回来</Text>
          <Text style={styles.subtitle}>请输入手机号和验证码登录</Text>
        </View>

        {/* 输入区域 */}
        <View style={styles.inputSection}>
          {/* 手机号输入 */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>手机号</Text>
            <TextInput
              style={styles.input}
              value={phoneNumber}
              onChangeText={setPhoneNumber}
              placeholder="请输入手机号"
              placeholderTextColor="rgba(0, 0, 0, 0.4)"
              keyboardType="phone-pad"
              maxLength={11}
              editable={!loading}
            />
          </View>

          {/* 验证码输入 */}
          <View style={styles.inputContainer}>
            <Text style={styles.label}>验证码</Text>
            <View style={styles.codeRow}>
              <TextInput
                ref={codeInputRef}
                style={[styles.input, styles.codeInput]}
                value={verificationCode}
                onChangeText={setVerificationCode}
                placeholder="请输入6位验证码"
                placeholderTextColor="rgba(0, 0, 0, 0.4)"
                keyboardType="number-pad"
                maxLength={6}
                editable={!loading}
              />
              <TouchableOpacity
                style={[
                  styles.codeButton,
                  (countdown > 0 || loading) && styles.codeButtonDisabled
                ]}
                onPress={handleGetCode}
                disabled={countdown > 0 || loading}
              >
                <Text style={styles.codeButtonText}>
                  {countdown > 0 ? `${countdown}秒` : '获取验证码'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* 登录按钮 */}
        <TouchableOpacity
          style={[
            styles.loginButton,
            loading && styles.loginButtonDisabled
          ]}
          onPress={handleLogin}
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#FF6B9D" />
          ) : (
            <Text style={styles.loginButtonText}>登录</Text>
          )}
        </TouchableOpacity>

        {/* 提示文字 */}
        <Text style={styles.hintText}>
          验证码仅用于演示，输入任意6位数字即可
        </Text>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 30,
    paddingTop: 60,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 60,
  },
  title: {
    fontSize: 32,
    color: '#333333',
    fontWeight: 'bold',
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
  },
  inputSection: {
    marginBottom: 40,
  },
  inputContainer: {
    marginBottom: 24,
  },
  label: {
    fontSize: 16,
    color: '#333333',
    marginBottom: 8,
    fontWeight: '500',
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#333333',
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  codeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  codeInput: {
    flex: 1,
  },
  codeButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  codeButtonDisabled: {
    opacity: 0.5,
  },
  codeButtonText: {
    color: '#FF6B9D',
    fontSize: 14,
    fontWeight: '500',
  },
  loginButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    marginBottom: 20,
  },
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonText: {
    color: '#FF6B9D',
    fontSize: 18,
    fontWeight: 'bold',
  },
  hintText: {
    fontSize: 12,
    color: '#999999',
    textAlign: 'center',
  },
});

