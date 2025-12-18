import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { useUser } from '../src/contexts/UserContext';

export default function HomeScreen() {
  const router = useRouter();
  const { userId, isLoading, isLoggedIn } = useUser();
  
  useEffect(() => {
    // 等待用户信息加载完成
    if (isLoading) {
      return;
    }

    // 延迟导航，确保根布局组件已挂载
    const timer = setTimeout(() => {
      if (isLoggedIn && userId) {
        // 用户已登录，跳转到主界面
        router.replace('/home');
      } else {
        // 用户未登录，跳转到登录界面
        router.replace('/login');
      }
    }, 100);
    
    return () => clearTimeout(timer);
  }, [isLoading, isLoggedIn, userId]);

  // 显示加载指示器，避免空白屏幕
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#E8D5FF' }}>
      <ActivityIndicator size="large" color="#6B4FA0" />
    </View>
  );
}
