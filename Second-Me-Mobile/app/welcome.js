import { View, Text, StyleSheet, TouchableOpacity, StatusBar } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';

export default function WelcomeScreen() {
  return (
    <LinearGradient
      colors={['#E8D5FF', '#9B7EDE', '#6B4FA0']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="light-content" />
      
      {/* 顶部文字区域 */}
      <View style={styles.textContainer}>
        <Text style={styles.mainText}>我是你的 第二自我 ——</Text>
        <Text style={styles.subText}>由你的记忆塑造。</Text>
        <Text style={styles.questionText}>准备好塑造我了吗?</Text>
      </View>

      {/* 手托球体区域 */}
      <View style={styles.sphereContainer}>
        <View style={styles.handsContainer}>
          {/* 左手 */}
          <View style={[styles.hand, styles.leftHand]} />
          {/* 右手 */}
          <View style={[styles.hand, styles.rightHand]} />
        </View>
        
        {/* 发光球体 */}
        <TouchableOpacity 
          style={styles.sphere}
          onPress={() => router.push('/name-input')}
          activeOpacity={0.8}
        >
          <View style={styles.sphereGlow}>
            <Text style={styles.startText}>开始</Text>
          </View>
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
    paddingBottom: 40,
  },
  textContainer: {
    alignItems: 'center',
    marginTop: 80,
    marginBottom: 60,
  },
  mainText: {
    fontSize: 24,
    color: '#FFFFFF',
    fontWeight: '500',
    marginBottom: 12,
    textAlign: 'center',
  },
  subText: {
    fontSize: 20,
    color: '#FFFFFF',
    fontWeight: '400',
    marginBottom: 12,
    textAlign: 'center',
  },
  questionText: {
    fontSize: 22,
    color: '#FFFFFF',
    fontWeight: '500',
    textAlign: 'center',
  },
  sphereContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
    position: 'relative',
  },
  handsContainer: {
    position: 'absolute',
    width: 200,
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
  },
  hand: {
    position: 'absolute',
    width: 80,
    height: 100,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 40,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.5)',
  },
  leftHand: {
    left: 20,
    transform: [{ rotate: '-20deg' }],
  },
  rightHand: {
    right: 20,
    transform: [{ rotate: '20deg' }],
  },
  sphere: {
    width: 140,
    height: 140,
    borderRadius: 70,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 40,
  },
  sphereGlow: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#FFFFFF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 10,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.6)',
  },
  startText: {
    fontSize: 32,
    color: '#6B4FA0',
    fontWeight: 'bold',
  },
});

