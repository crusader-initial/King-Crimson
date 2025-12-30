import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TextInput, 
  TouchableOpacity, 
  FlatList, 
  KeyboardAvoidingView, 
  Platform,
  ActivityIndicator 
} from 'react-native';
import { useNavigation } from 'expo-router';
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
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [conversationId, setConversationId] = useState(null);
  const [roleId, setRoleId] = useState(null);
  const [roleName, setRoleName] = useState('"我"'); // 默认显示"我"
  const flatListRef = useRef();

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

        // 2. 获取或创建会话
        const conversationResponse = await createConversation(
          userId, 
          currentRoleId, 
          'role', 
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
            roleId,  // 接收者：角色ID
            messageText,
            'text'
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
            userId,  // 接收者：用户ID
            response.answer,
            'text'
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

  const renderMessage = ({ item }) => (
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

  // 设置导航栏标题
  useLayoutEffect(() => {
    navigation.setOptions({
      title: roleName,
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

  if (loadingHistory) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <ActivityIndicator size="large" color="#FF6B9D" />
        <Text style={styles.loadingText}>加载聊天记录...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={100}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
      />

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Type a message..."
          multiline
        />
        <TouchableOpacity 
          style={[styles.sendButton, (!inputText.trim() || loading) && styles.disabledButton]} 
          onPress={handleSend}
          disabled={!inputText.trim() || loading}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.sendButtonText}>Send</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFE5F0',
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
  userText: {
    color: '#fff',
  },
  aiText: {
    color: '#000',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    alignItems: 'flex-end',
  },
  input: {
    flex: 1,
    backgroundColor: '#f0f0f0',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingTop: 10,
    paddingBottom: 10,
    maxHeight: 100,
    marginRight: 10,
    fontSize: 16,
  },
  sendButton: {
    backgroundColor: '#B6D9FF',
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 10,
    justifyContent: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  sendButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
