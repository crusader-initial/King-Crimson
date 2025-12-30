import { View, Text, StyleSheet, TouchableOpacity, StatusBar } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';

export default function WelcomeScreen() {
  return (
    <LinearGradient
      colors={['#FFE5F0', '#E5F0FF', '#D6E8FF']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="dark-content" />
      
      {/* 顶部文字区域 */}
      <View style={styles.textContainer}>
        <Text style={styles.mainText}>我是你的 第二自我</Text>
        <Text style={styles.subText}>由你的记忆塑造</Text>
      </View>

      {/* 开始按钮 */}
      <TouchableOpacity 
        style={styles.startButton}
        onPress={() => router.push('/name-input')}
        activeOpacity={0.8}
      >
        <Text style={styles.startText}>开始</Text>
      </TouchableOpacity>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 30,
  },
  textContainer: {
    alignItems: 'center',
    marginBottom: 80,
  },
  mainText: {
    fontSize: 28,
    color: '#333333',
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  subText: {
    fontSize: 18,
    color: '#666666',
    textAlign: 'center',
  },
  startButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    paddingVertical: 16,
    paddingHorizontal: 60,
    minWidth: 200,
  },
  startText: {
    fontSize: 18,
    color: '#FF6B9D',
    fontWeight: '600',
    textAlign: 'center',
  },
});

