import { useEffect, useState, useLayoutEffect } from 'react';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { UserProvider } from '../src/contexts/UserContext';
import CustomSplashScreen from '../components/SplashScreen';

// 防止原生启动画面自动隐藏
SplashScreen.preventAutoHideAsync();

// 在模块加载时立即尝试隐藏原生启动画面
let hideSplashPromise = null;
try {
  hideSplashPromise = SplashScreen.hideAsync();
} catch (e) {
  console.warn('Error hiding splash screen at module level:', e);
}

export default function Layout() {
  const [isSplashVisible, setIsSplashVisible] = useState(true);
  const [isAppReady, setIsAppReady] = useState(false);

  // 使用 useLayoutEffect 在 DOM 更新之前同步执行
  useLayoutEffect(() => {
    // 立即隐藏原生启动画面
    async function hideNativeSplash() {
      try {
        // 如果模块级别的隐藏还没完成，等待它
        if (hideSplashPromise) {
          await hideSplashPromise;
        } else {
          await SplashScreen.hideAsync();
        }
      } catch (e) {
        console.warn('Error hiding splash screen:', e);
      }
    }

    hideNativeSplash();
  }, []);

  useEffect(() => {
    // 应用初始化
    async function prepare() {
      try {
        // 可以在这里执行初始化操作
        // 例如：加载字体、初始化数据等
        await new Promise(resolve => setTimeout(resolve, 300)); // 初始化时间
        
        setIsAppReady(true);
      } catch (e) {
        console.warn(e);
        setIsAppReady(true);
      }
    }

    prepare();
  }, []);

  const handleAnimationFinish = () => {
    // 动画播放完成且应用已准备好，才隐藏启动画面
    if (isAppReady) {
      setIsSplashVisible(false);
    } else {
      // 如果应用还没准备好，等待一下
      setTimeout(() => {
        setIsSplashVisible(false);
      }, 500);
    }
  };

  if (isSplashVisible) {
    return (
      <CustomSplashScreen 
        onFinish={handleAnimationFinish}
      />
    );
  }

  return (
    <UserProvider>
      <Stack
        screenOptions={{
          headerShown: false, // 隐藏所有页面的默认头部
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="login" />
        <Stack.Screen name="welcome" />
        <Stack.Screen name="name-input" />
        <Stack.Screen name="info-collection" />
        <Stack.Screen name="home" />
        <Stack.Screen name="upload" options={{ title: 'Upload Character', headerShown: true }} />
        <Stack.Screen name="chat" options={{ title: 'Chat with AI', headerShown: true }} />
      </Stack>
    </UserProvider>
  );
}
