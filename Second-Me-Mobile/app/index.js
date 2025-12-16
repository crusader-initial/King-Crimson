import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';

export default function HomeScreen() {
  const router = useRouter();
  
  useEffect(() => {
    // 延迟导航，确保根布局组件已挂载
    const timer = setTimeout(() => {
      router.replace('/welcome');
    }, 100);
    
    return () => clearTimeout(timer);
  }, []);

  // 显示加载指示器，避免空白屏幕
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#E8D5FF' }}>
      <ActivityIndicator size="large" color="#6B4FA0" />
    </View>
  );
}
