import { useState, useRef, useEffect, useLayoutEffect, useMemo } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TextInput, 
  TouchableOpacity, 
  FlatList, 
  Image,
  Modal,
  Pressable,
  KeyboardAvoidingView, 
  Platform,
  ActivityIndicator,
  Keyboard,
  InteractionManager
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { 
  sendChatMessage, 
  getRoleByUuid, 
  createConversation, 
  getMessagesByConversationId,
  createMessage
} from '../src/services/api';
import { useUser } from '../src/contexts/UserContext';

export default function ChatScreen() {
  const { userId } = useUser();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [conversationId, setConversationId] = useState(null);
  const [roleId, setRoleId] = useState(null);
  const [roleName, setRoleName] = useState('"我"'); // 默认显示"我"
  const flatListRef = useRef();
  const contentHeightRef = useRef(0);
  const isAutoScrollingRef = useRef(false);
  const hasInitialScrollRef = useRef(false);
  const [showAddSheet, setShowAddSheet] = useState(false);
  const displayMessages = useMemo(() => {
    const sorted = [...messages].sort((a, b) => {
      const aTime = a?.timestamp ? new Date(a.timestamp).getTime() : 0;
      const bTime = b?.timestamp ? new Date(b.timestamp).getTime() : 0;
      return aTime - bTime;
    });

    const formatTimeLabel = (date) => {
      const d = new Date(date);
      const now = new Date();
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const yesterdayStart = new Date(todayStart);
      yesterdayStart.setDate(todayStart.getDate() - 1);

      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');

      if (d >= todayStart) {
        return `${hh}:${mm}`;
      }
      if (d >= yesterdayStart) {
        return `昨天 ${hh}:${mm}`;
      }

      const yyyy = d.getFullYear();
      const MM = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      return `${yyyy}/${MM}/${dd} ${hh}:${mm}`;
    };

    const grouped = [];
    let prevTime = null;
    for (const msg of sorted) {
      const msgTime = msg?.timestamp ? new Date(msg.timestamp).getTime() : null;
      const shouldInsertTime =
        msgTime !== null &&
        (prevTime === null || msgTime - prevTime >= 5 * 60 * 1000);

      if (shouldInsertTime) {
        grouped.push({
          id: `time-${msgTime}-${msg.id}`,
          type: 'time',
          label: formatTimeLabel(msg.timestamp),
        });
      }

      grouped.push({ ...msg, type: 'message' });
      prevTime = msgTime ?? prevTime;
    }
    return grouped;
  }, [messages]);

  // 初始化：获取或创建会话，并加载历史消息
  useEffect(() => {
    const initChat = async () => {
      if (!userId) {
        setLoadingHistory(false);
        return;
      }

      try {
        // 1. 获取角色信息
        const roleResponse = await getRoleByUuid(userId);
        if (!roleResponse || !roleResponse.data || !roleResponse.data.id) {
          console.warn('无法获取角色信息');
          setLoadingHistory(false);
          return;
        }

        const currentRoleId = roleResponse.data.id;
        const currentRoleName = roleResponse.data.name || '"我"';
        setRoleId(currentRoleId);
        setRoleName(currentRoleName);

        // 2. 获取或创建会话（传入参与者ID列表和会话类型）
        const conversationResponse = await createConversation(
          [userId, currentRoleId],  // 参与者列表：用户ID和角色ID
          'single',  // 单聊
          '和"我"的对话'
        );
        
        if (conversationResponse && conversationResponse.data && conversationResponse.data.conversation_id) {
          const convId = conversationResponse.data.conversation_id;
          setConversationId(convId);

          // 3. 加载历史消息（正序，从旧到新）
          const messagesResponse = await getMessagesByConversationId(convId, null, 0, false);
          
          if (messagesResponse && messagesResponse.data && messagesResponse.data.length > 0) {
            // 转换消息格式
            const formattedMessages = messagesResponse.data.map(msg => {
              // 判断发送者是用户还是AI（需要转换为字符串比较）
              const senderIdStr = String(msg.sender_id);
              const userIdStr = String(userId);
              const sender = senderIdStr === userIdStr ? 'user' : 'ai';
              return {
                id: msg.id,
                text: msg.content,
                sender: sender,
                timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
              };
            });
            
            setMessages(formattedMessages);
          }
        }
      } catch (error) {
        console.error('初始化聊天失败:', error);
      } finally {
        setLoadingHistory(false);
      }
    };

    initChat();
  }, [userId]);

  const handleSend = async () => {
    if (!inputText.trim() || loading || !conversationId || !roleId) return;

    const userMessage = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = inputText;
    setInputText('');
    setLoading(true);

    try {
      // 保存用户消息到数据库
      if (conversationId && roleId) {
        try {
          await createMessage(
            conversationId,
            userId,  // 发送者：用户ID
            messageText,
            'text',
            null,
            'user'  // 发送者类型：用户
          );
        } catch (msgError) {
          console.error('保存用户消息失败:', msgError);
        }
      }

      // 获取历史消息（用于构建上下文，排除刚添加的用户消息）
      // 只取最近10条历史消息，避免上下文过长
      const recentHistory = messages.slice(-10);
      
      // 发送消息到AI（使用roleId和历史消息）
      const response = await sendChatMessage(messageText, roleId, recentHistory);
      
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        text: response.answer,
        sender: 'ai',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, aiMessage]);

      // 保存AI回复到数据库
      if (conversationId && roleId && response.answer) {
        try {
          await createMessage(
            conversationId,
            roleId,  // 发送者：角色ID（AI）
            response.answer,
            'text',
            null,
            'ai'  // 发送者类型：AI
          );
        } catch (msgError) {
          console.error('保存AI消息失败:', msgError);
        }
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        text: "抱歉，我无法处理这个请求。",
        sender: 'system',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = ({ item }) => {
    if (item.type === 'time') {
      return (
        <View style={styles.timeSeparator}>
          <Text style={styles.timeSeparatorText}>——  {item.label}  ——</Text>
        </View>
      );
    }

    return (
      <View style={[
        styles.messageBubble,
        item.sender === 'user' ? styles.userBubble : styles.aiBubble,
        item.sender === 'system' && styles.systemBubble
      ]}>
        <Text style={[
          styles.messageText,
          item.sender === 'user' ? styles.userText : styles.aiText
        ]}>
          {item.text}
        </Text>
      </View>
    );
  };

  // 设置导航栏标题
  useLayoutEffect(() => {
    navigation.setOptions({
      title: roleName,
      headerTitleAlign: 'center',
      headerStyle: {
        backgroundColor: '#F5F6F8',
      },
      headerShadowVisible: false,
    });
  }, [navigation, roleName]);

  // 自动滚动到底部
  useEffect(() => {
    if (messages.length > 0 && !loadingHistory) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages, loadingHistory]);

  useEffect(() => {
    const showSub = Keyboard.addListener('keyboardDidShow', () => {
      setKeyboardVisible(true);
    });
    const hideSub = Keyboard.addListener('keyboardDidHide', () => {
      setKeyboardVisible(false);
    });

    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  const bottomInset = insets.bottom;
  const listPaddingBottom = 12 + bottomInset;
  const inputContainerStyle = { paddingBottom: 16 + bottomInset };
  const addSheetBottomOffset = 72 + bottomInset;
  const scrollToBottom = (animated = true) => {
    flatListRef.current?.scrollToEnd({ animated });
  };
  const scrollToBottomDelayed = () => {
    isAutoScrollingRef.current = true;
    scrollToBottom(false);
    requestAnimationFrame(() => scrollToBottom(false));
    InteractionManager.runAfterInteractions(() => scrollToBottom(false));
    setTimeout(() => {
      scrollToBottom(false);
      isAutoScrollingRef.current = false;
    }, 120);
  };
  const handleAddPress = () => setShowAddSheet(true);
  const handleCloseSheet = () => setShowAddSheet(false);
  const handleAddAction = (action) => {
    setShowAddSheet(false);
    console.log(`选择 ${action}`);
  };

  useEffect(() => {
    if (keyboardVisible) {
      scrollToBottomDelayed();
    }
  }, [keyboardVisible]);

  useEffect(() => {
    if (!loadingHistory) {
      scrollToBottomDelayed();
    }
  }, [loadingHistory, messages.length]);

  if (loadingHistory) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <ActivityIndicator size="large" color="#FF6B9D" />
        <Text style={styles.loadingText}>加载聊天记录...</Text>
      </View>
    );
  }

  return (
    <LinearGradient
      colors={['#FFE5F0', '#E5F0FF', '#D6E8FF']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <KeyboardAvoidingView 
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 10 : 25}
      >
      <FlatList
        ref={flatListRef}
        data={displayMessages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        style={styles.messageListContainer}
        contentContainerStyle={[styles.messageList, { paddingBottom: listPaddingBottom }]}
        onLayout={() => {
          if (!hasInitialScrollRef.current && !loadingHistory) {
            hasInitialScrollRef.current = true;
            scrollToBottomDelayed();
          }
        }}
        onContentSizeChange={(_, height) => {
          contentHeightRef.current = height;
          scrollToBottom(false);
        }}
        scrollEventThrottle={16}
      />

      <View style={[styles.inputContainer, inputContainerStyle]}>
        <TouchableOpacity style={styles.iconButton} activeOpacity={0.7} onPress={handleAddPress}>
          <Image
            source={require('../assets/chat-input-add.png')}
            style={styles.iconImage}
            resizeMode="contain"
          />
        </TouchableOpacity>

        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="说点什么..."
          placeholderTextColor="#9AA0A6"
          multiline
          onFocus={scrollToBottomDelayed}
        />
        </View>

        <TouchableOpacity
          style={styles.iconButton}
          activeOpacity={0.7}
          onPress={inputText.trim() ? handleSend : undefined}
          disabled={!inputText.trim() || loading}
        >
          <Image
            source={
              inputText.trim()
                ? require('../assets/chat-input-send.png')
                : require('../assets/chat-input-voice.png')
            }
            style={styles.iconImage}
            resizeMode="contain"
          />
        </TouchableOpacity>
      </View>


      <Modal transparent visible={showAddSheet} animationType="fade" onRequestClose={handleCloseSheet}>
        <Pressable style={styles.addSheetBackdrop} onPress={handleCloseSheet}>
          <View
            style={[styles.addSheetContainer, { bottom: addSheetBottomOffset }]}
            onStartShouldSetResponder={() => true}
          >
            <TouchableOpacity
              style={styles.addSheetItem}
              onPress={() => handleAddAction('相机')}
              activeOpacity={0.7}
            >
              <Image
                source={require('../assets/chat-input-camera.png')}
                style={styles.addSheetIcon}
                resizeMode="contain"
              />
              <Text style={styles.addSheetText}>相机</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.addSheetItem}
              onPress={() => handleAddAction('照片')}
              activeOpacity={0.7}
            >
              <Image
                source={require('../assets/chat-input-album.png')}
                style={styles.addSheetIcon}
                resizeMode="contain"
              />
              <Text style={styles.addSheetText}>照片</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.addSheetItem}
              onPress={() => handleAddAction('文档')}
              activeOpacity={0.7}
            >
              <Image
                source={require('../assets/chat-input-document.png')}
                style={styles.addSheetIcon}
                resizeMode="contain"
              />
              <Text style={styles.addSheetText}>文档</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
    fontSize: 14,
  },
  messageList: {
    padding: 15,
    paddingBottom: 20,
  },
  messageListContainer: {
    flex: 1,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 20,
    marginBottom: 10,
  },
  userBubble: {
    backgroundColor: '#FFB6C1',
    alignSelf: 'flex-end',
    borderBottomRightRadius: 5,
  },
  aiBubble: {
    backgroundColor: '#fff',
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  systemBubble: {
    backgroundColor: '#ff3b30',
    alignSelf: 'center',
    borderRadius: 10,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  timeSeparator: {
    alignItems: 'center',
    marginVertical: 10,
  },
  timeSeparatorText: {
    fontSize: 12,
    color: '#9AA0A6',
  },
  userText: {
    color: '#fff',
  },
  aiText: {
    color: '#000',
  },
  inputContainer: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 12,
    backgroundColor: '#F5F6F8',
    borderTopWidth: 1,
    borderTopColor: '#ECEFF3',
    alignItems: 'center',
    gap: 8,
    minHeight: 56,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
  },
  iconImage: {
    width: 30,
    height: 30,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#E6E9EE',
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  input: {
    minHeight: 30,
    maxHeight: 100,
    fontSize: 15,
    color: '#111',
    padding: 0,
  },
  addSheetBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'flex-end',
  },
  addSheetContainer: {
    position: 'absolute',
    left: 24,
    paddingBottom: 28,
  },
  addSheetItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    gap: 12,
  },
  addSheetIcon: {
    width: 22,
    height: 22,
  },
  addSheetText: {
    fontSize: 16,
    color: '#111',
    fontWeight: '500',
  },
});
