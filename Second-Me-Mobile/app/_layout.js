import { Stack } from 'expo-router';

export default function Layout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false, // 隐藏所有页面的默认头部
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="welcome" />
      <Stack.Screen name="name-input" />
      <Stack.Screen name="info-collection" />
      <Stack.Screen name="home" />
      <Stack.Screen name="upload" options={{ title: 'Upload Character', headerShown: true }} />
      <Stack.Screen name="chat" options={{ title: 'Chat with AI', headerShown: true }} />
    </Stack>
  );
}
