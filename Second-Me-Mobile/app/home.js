import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  StatusBar
} from 'react-native';
import { router } from 'expo-router';

const BOTTOM_NAV_HEIGHT = 80; // 底部导航栏高度

export default function HomeScreen() {
  const handleChatPress = () => {
    // 点击聊天框，进入完全聊天界面
    router.push('/chat');
  };

  const handleUploadPress = () => {
    // 点击上传按钮，进入上传文件界面
    router.push('/upload');
  };

  const handleTabPress = (tab) => {
    // 处理底部导航栏点击
    // TODO: 实现不同tab的页面切换
    console.log(`切换到 ${tab} 标签`);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />
      
      {/* "我"栏目内容区域 */}
      <View style={styles.contentArea}>
        {/* 这里可以添加"我"tab的具体内容 */}
      </View>
      
      {/* 底部操作区域 */}
      <View style={styles.bottomSection}>
        {/* 聊天框和上传按钮 */}
        <View style={styles.actionRow}>
          <TouchableOpacity 
            style={styles.chatBox}
            onPress={handleChatPress}
            activeOpacity={0.8}
          >
            <Text style={styles.chatPlaceholder}>和"我"聊聊,丰富记忆...</Text>
            <Text style={styles.chatIcon}>💬</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.uploadButton}
            onPress={handleUploadPress}
            activeOpacity={0.8}
          >
            <Text style={styles.uploadIcon}>📄</Text>
            <Text style={styles.uploadText}>上传</Text>
          </TouchableOpacity>
        </View>

        {/* 底部导航栏 */}
        <View style={styles.bottomNav}>
          <TouchableOpacity 
            style={[styles.navItem, styles.navItemActive]}
            onPress={() => handleTabPress('me')}
            activeOpacity={0.7}
          >
            <Text style={[styles.navLabel, styles.navLabelActive]}>我</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.navItem}
            onPress={() => handleTabPress('friends')}
            activeOpacity={0.7}
          >
            <Text style={styles.navLabel}>好友</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.navItem}
            onPress={() => handleTabPress('discover')}
            activeOpacity={0.7}
          >
            <Text style={styles.navLabel}>发现</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFE5F0',
  },
  contentArea: {
    flex: 1,
    paddingTop: 20,
    paddingHorizontal: 20,
    paddingBottom: BOTTOM_NAV_HEIGHT + 100, // 为底部操作区域留出空间
  },
  bottomSection: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 10,
    gap: 12,
  },
  chatBox: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    paddingHorizontal: 20,
    paddingVertical: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  chatPlaceholder: {
    color: '#999999',
    fontSize: 16,
    flex: 1,
  },
  chatIcon: {
    fontSize: 20,
    marginLeft: 10,
  },
  uploadButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    paddingHorizontal: 20,
    paddingVertical: 18,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 80,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  uploadIcon: {
    fontSize: 20,
    marginBottom: 4,
  },
  uploadText: {
    color: '#333333',
    fontSize: 12,
    fontWeight: '500',
  },
  bottomNav: {
    height: BOTTOM_NAV_HEIGHT,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    paddingTop: 12,
    paddingBottom: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0, 0, 0, 0.1)',
  },
  navItem: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    paddingVertical: 8,
  },
  navItemActive: {
    backgroundColor: 'rgba(255, 107, 157, 0.1)',
    borderRadius: 8,
  },
  navLabel: {
    color: '#666666',
    fontSize: 14,
    fontWeight: '500',
  },
  navLabelActive: {
    color: '#FF6B9D',
    fontWeight: '600',
  },
});
