import { Stack } from 'expo-router';

export default function Layout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: {
          backgroundColor: '#f4511e',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Second Me' }} />
      <Stack.Screen name="upload" options={{ title: 'Upload Character' }} />
      <Stack.Screen name="chat" options={{ title: 'Chat with AI' }} />
    </Stack>
  );
}
