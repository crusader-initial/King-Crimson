import { useEffect, useRef } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import LottieView from 'lottie-react-native';

const { width, height } = Dimensions.get('window');

export default function CustomSplashScreen({ onFinish }) {
  const animation = useRef(null);

  useEffect(() => {
    // 确保动画在组件挂载后立即播放
    const timer = setTimeout(() => {
      if (animation.current) {
        animation.current.play();
      }
    }, 50);

    return () => clearTimeout(timer);
  }, []);

  return (
    <View style={styles.container}>
      <LottieView
        ref={animation}
        source={require('../assets/splash-animation.json')}
        style={styles.animation}
        loop={false}
        onAnimationFinish={onFinish}
        autoPlay={true}
        resizeMode="contain"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFE5F0',
  },
  animation: {
    width: width,
    height: height,
  },
});

