import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Image,
  StatusBar,
  Modal,
  Pressable
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useState } from 'react';
import { router } from 'expo-router';

const BOTTOM_NAV_HEIGHT = 80; // 底部导航栏高度
const ACTION_ROW_HEIGHT = 56; // 聊天框与上传按钮高度

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const topBarHeight = 80;
  const sideTitleTop = insets.top + (topBarHeight - 20) / 2 + 6;
  const [showSideSheet, setShowSideSheet] = useState(false);
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
  const handleOpenSideSheet = () => setShowSideSheet(true);
  const handleCloseSideSheet = () => setShowSideSheet(false);

  return (
    <LinearGradient
      colors={['#FFE5F0', '#E5F0FF', '#D6E8FF']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="dark-content" />
      <SafeAreaView style={styles.topSafeArea} edges={['top']}>
        <View style={[styles.topBar, { height: topBarHeight }]}>
          <TouchableOpacity
            style={[styles.topBarMoreButton, { top: (topBarHeight - 24) / 2 + 6 }]}
            activeOpacity={0.7}
            onPress={handleOpenSideSheet}
          >
            <Image
              source={require('../assets/home-more-icon.png')}
              style={styles.topBarMoreIcon}
              resizeMode="contain"
            />
          </TouchableOpacity>
          <Text style={styles.topBarTitle}>知我</Text>
        </View>
      </SafeAreaView>
      {/* "我"栏目内容区域 */}
      <View style={[styles.contentArea, { paddingBottom: BOTTOM_NAV_HEIGHT + 100 + insets.bottom }]}>
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
            <Image
              source={require('../assets/home-upload-icon.png')}
              style={styles.uploadIcon}
              resizeMode="contain"
            />
            <Text style={styles.uploadText}>上传</Text>
          </TouchableOpacity>
        </View>

        {/* 底部导航栏 */}
        <View
          style={[
            styles.bottomNav,
            {
              height: BOTTOM_NAV_HEIGHT + insets.bottom,
              paddingBottom: 20 + insets.bottom,
            },
          ]}
        >
          <TouchableOpacity 
            style={styles.navItem}
            onPress={() => handleTabPress('me')}
            activeOpacity={0.7}
          >
            <Image
              source={require('../assets/home-home-icon.png')}
              style={[styles.navIcon, styles.navIconActive]}
              resizeMode="contain"
            />
            <Text style={[styles.navLabel, styles.navLabelActive]}>首页</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.navItem}
            onPress={() => handleTabPress('friends')}
            activeOpacity={0.7}
          >
            <Image
              source={require('../assets/home-friend-icon.png')}
              style={styles.navIcon}
              resizeMode="contain"
            />
            <Text style={styles.navLabel}>好友</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.navItem}
            onPress={() => handleTabPress('discover')}
            activeOpacity={0.7}
          >
            <Image
              source={require('../assets/home-Moments-icon.png')}
              style={styles.navIcon}
              resizeMode="contain"
            />
            <Text style={styles.navLabel}>发现</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Modal transparent visible={showSideSheet} animationType="fade" onRequestClose={handleCloseSideSheet}>
        <Pressable style={styles.sideSheetBackdrop} onPress={handleCloseSideSheet}>
          <View style={styles.sideSheetPanel} onStartShouldSetResponder={() => true}>
            <Text style={[styles.sideSheetTitle, { marginTop: sideTitleTop }]}>知我</Text>
            <View style={styles.sideSheetSearchWrapper}>
              <View style={styles.sideSheetSearchBox}>
                <Image
                  source={require('../assets/home-memory-search.png')}
                  style={styles.sideSheetSearchIcon}
                  resizeMode="contain"
                />
                <Text style={styles.sideSheetSearchText}>搜索</Text>
              </View>
            </View>
            <View style={styles.sideSheetDivider} />
            <View style={[styles.sideSheetFooter, { paddingBottom: insets.bottom + 20 }]}>
              <TouchableOpacity style={styles.sideSheetSettingsButton} activeOpacity={0.8}>
                <Text style={styles.sideSheetSettingsIcon}>⚙</Text>
                <Text style={styles.sideSheetSettingsText}>设置</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Pressable>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topSafeArea: {
    backgroundColor: 'rgba(255, 255, 255, 0)',
  },
  topBar: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0)',
  },
  topBarMoreButton: {
    position: 'absolute',
    left: 16,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  topBarMoreIcon: {
    width: 20,
    height: 20,
  },
  topBarTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginTop: 6,
  },
  sideSheetBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
  },
  sideSheetPanel: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    width: '70%',
    backgroundColor: '#1B1B1B',
    paddingTop: 16,
    paddingHorizontal: 16,
  },
  sideSheetTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  sideSheetSearchWrapper: {
    height: 40,
    marginTop: 12,
    marginBottom: 8,
    justifyContent: 'center',
  },
  sideSheetSearchBox: {
    height: 40,
    borderRadius: 10,
    backgroundColor: '#4B4B4B',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 8,
  },
  sideSheetSearchIcon: {
    width: 18,
    height: 18,
  },
  sideSheetSearchText: {
    color: '#FFFFFF',
    fontSize: 14,
  },
  sideSheetDivider: {
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    marginTop: 8,
  },
  sideSheetFooter: {
    marginTop: 'auto',
    paddingBottom: 20,
    paddingHorizontal: 2,
  },
  sideSheetSettingsButton: {
    height: 40,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  sideSheetSettingsIcon: {
    color: '#111111',
    fontSize: 18,
  },
  sideSheetSettingsText: {
    color: '#111111',
    fontSize: 15,
    fontWeight: '600',
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
    height: ACTION_ROW_HEIGHT,
    paddingHorizontal: 20,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  chatPlaceholder: {
    color: '#999999',
    fontSize: 16,
    lineHeight: 20,
    includeFontPadding: false,
    flex: 1,
  },
  chatIcon: {
    fontSize: 20,
    marginLeft: 10,
  },
  uploadButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    height: ACTION_ROW_HEIGHT,
    paddingHorizontal: 20,
    paddingVertical: 6,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 80,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  uploadIcon: {
    width: 18,
    height: 18,
    marginBottom: 2,
  },
  uploadText: {
    color: '#333333',
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 14,
    includeFontPadding: false,
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
  navLabel: {
    color: '#666666',
    fontSize: 14,
    fontWeight: '500',
    marginTop: 4,
  },
  navLabelActive: {
    color: '#FF6B9D',
    fontWeight: '600',
  },
  navIcon: {
    width: 22,
    height: 22,
    tintColor: '#666666',
  },
  navIconActive: {
    tintColor: '#FF6B9D',
  },
});
