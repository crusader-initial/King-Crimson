import { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  StatusBar,
  Image,
  Dimensions
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';

const { width, height } = Dimensions.get('window');
const BOTTOM_NAV_HEIGHT = 80; // 底部导航栏高度

export default function HomeScreen() {
  // 进度暂时写死为45%，后续再实现动态计算
  const progress = 45;

  const handleChatPress = () => {
    // 点击聊天框，进入完全聊天界面
    router.push('/chat');
  };

  const handleRecordPress = () => {
    // 点击记录按钮，进入上传文件界面
    router.push('/upload');
  };

  const handleTabPress = (tab) => {
    // 处理底部导航栏点击
    // TODO: 实现不同tab的页面切换
    console.log(`切换到 ${tab} 标签`);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* 封面图片 - 占据整个屏幕 */}
      <View style={styles.coverContainer}>
        <Image
          source={require('../assets/default-cover.png')}
          style={styles.coverImage}
          resizeMode="cover"
        />
        {/* 封面渐变遮罩，使上方内容更清晰 */}
        <LinearGradient
          colors={['rgba(0,0,0,0)', 'rgba(0,0,0,0.2)', 'rgba(0,0,0,0.5)']}
          style={styles.coverOverlay}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
        />
      </View>

      {/* 顶部操作栏 - 覆盖在封面上 */}
      <View style={styles.topBar}>
        <TouchableOpacity style={styles.menuButton} activeOpacity={0.7}>
          <Text style={styles.menuIcon}>☰</Text>
        </TouchableOpacity>
      </View>

      {/* 进度条 - 覆盖在封面上方 */}
      <View style={styles.progressContainer}>
        <TouchableOpacity style={styles.progressBar} activeOpacity={0.8}>
          <View style={styles.progressBarLeft}>
            <Text style={styles.progressIcon}>📄</Text>
          </View>
          <View style={styles.progressBarCenter}>
            <Text style={styles.progressText}>塑造"我" {progress}%</Text>
          </View>
          <View style={styles.progressBarRight}>
            <Text style={styles.progressArrow}>→</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* 聊天框和记录按钮区域 - 覆盖在封面下方，确保不与导航栏重叠 */}
      <View style={styles.actionSection}>
        <TouchableOpacity 
          style={styles.chatBox}
          onPress={handleChatPress}
          activeOpacity={0.8}
        >
          <View style={styles.chatBoxContent}>
            <Text style={styles.chatPlaceholder}>和"我"聊聊,丰富记忆...</Text>
            <View style={styles.chatIconContainer}>
              <Text style={styles.chatIcon}>💬</Text>
            </View>
          </View>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.recordButton}
          onPress={handleRecordPress}
          activeOpacity={0.8}
        >
          <Text style={styles.recordIcon}>✎</Text>
          <Text style={styles.recordText}>记录</Text>
        </TouchableOpacity>
      </View>

      {/* 底部导航栏 */}
      <View style={styles.bottomNav}>
        <TouchableOpacity 
          style={[styles.navItem, styles.navItemActive]}
          onPress={() => handleTabPress('me')}
          activeOpacity={0.7}
        >
          <Text style={styles.navIcon}>🏠</Text>
          <Text style={styles.navLabel}>我</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.navItem}
          onPress={() => handleTabPress('friends')}
          activeOpacity={0.7}
        >
          <Text style={styles.navIcon}>😊</Text>
          <Text style={styles.navLabel}>好友</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.navItem}
          onPress={() => handleTabPress('discover')}
          activeOpacity={0.7}
        >
          <Text style={styles.navIcon}>🧭</Text>
          <Text style={styles.navLabel}>发现</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#6B4FA0',
  },
  coverContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: width,
    height: height,
  },
  coverImage: {
    width: '100%',
    height: '100%',
  },
  coverOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '50%',
  },
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 10,
    zIndex: 10,
  },
  menuButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    borderRadius: 22, // 椭圆形
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  menuIcon: {
    fontSize: 20,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  progressContainer: {
    position: 'absolute',
    top: height * 0.55,
    left: 0,
    right: 0,
    paddingHorizontal: 20,
    zIndex: 10,
  },
  progressBar: {
    flexDirection: 'row',
    backgroundColor: 'rgba(155, 126, 222, 0.85)', // 半透明
    borderRadius: 30, // 椭圆形
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  progressBarLeft: {
    marginRight: 14,
  },
  progressIcon: {
    fontSize: 22,
  },
  progressBarCenter: {
    flex: 1,
    alignItems: 'center',
  },
  progressText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
    letterSpacing: 0.5,
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  progressBarRight: {
    marginLeft: 14,
  },
  progressArrow: {
    fontSize: 22,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  actionSection: {
    position: 'absolute',
    bottom: BOTTOM_NAV_HEIGHT + 20, // 确保不与导航栏重叠，留出20px间距
    left: 0,
    right: 0,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    zIndex: 10,
  },
  chatBox: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.9)', // 半透明白色
    borderRadius: 28, // 椭圆形
    paddingHorizontal: 20,
    paddingVertical: 18,
    minHeight: 60,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.5)',
  },
  chatBoxContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  chatPlaceholder: {
    color: '#999',
    fontSize: 15,
    flex: 1,
  },
  chatIconContainer: {
    marginLeft: 10,
  },
  chatIcon: {
    fontSize: 20,
  },
  recordButton: {
    backgroundColor: 'rgba(107, 79, 160, 0.85)', // 半透明紫色
    borderRadius: 28, // 椭圆形
    paddingHorizontal: 24,
    paddingVertical: 18,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 76,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 10,
    elevation: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  recordIcon: {
    fontSize: 24,
    color: '#FFFFFF',
    marginBottom: 4,
  },
  recordText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  bottomNav: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: BOTTOM_NAV_HEIGHT,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    backgroundColor: 'rgba(107, 79, 160, 0.75)', // 半透明紫色
    paddingTop: 12,
    paddingBottom: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.25)',
    zIndex: 10,
  },
  navItem: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    paddingVertical: 8,
    borderRadius: 20, // 椭圆形点击区域
  },
  navItemActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)', // 激活状态半透明背景
    borderRadius: 20,
  },
  navIcon: {
    fontSize: 28,
    marginBottom: 4,
  },
  navLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '500',
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
});
