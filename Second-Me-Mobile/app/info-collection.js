import { useState, useRef, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TextInput, 
  TouchableOpacity, 
  StatusBar,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { 
  sendChatMessage, 
  sendInfoCollectionLLM,
  submitInfoCollection,
  getUserById,
  getRoleByUuid,
  createConversation,
  createMessage
} from '../src/services/api';
import { useUser } from '../src/contexts/UserContext';

export default function InfoCollectionScreen() {
  const { userId, userInfo } = useUser();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(1); // 当前问题序号 1-5
  const [userAnswers, setUserAnswers] = useState({}); // 存储用户回答
  const [isCompleted, setIsCompleted] = useState(false); // 是否已完成所有问题
  const [tempData, setTempData] = useState({
    description: '' // 暂存职业和喜好
  });
  const [conversationId, setConversationId] = useState(null); // 会话ID
  const [roleId, setRoleId] = useState(null); // 角色ID
  const flatListRef = useRef();

  // 问题模板（第一个问题是硬编码的，其他问题由后端根据系统prompt生成）
  const questionTemplates = {
    1: {
      text: '你创造了我！但现在的我.....是空的。你的记忆会给我形状。\n那么，先从这里开始吧--"我"的职业是什么？'
    }
  };

  // 初始化：发送第一个问题并创建会话记录
  useEffect(() => {
    const initMessage = {
      id: '0',
      text: questionTemplates[1].text,
      sender: 'ai',
      timestamp: new Date(),
    };
    setMessages([initMessage]);
    
    // 创建会话记录并保存初始消息
    const initConversation = async () => {
      try {
        // 获取角色信息以获取角色ID
        const roleResponse = await getRoleByUuid(userId);
        if (roleResponse && roleResponse.data && roleResponse.data.id) {
          const roleId = roleResponse.data.id;
          
          // 1. 创建会话
          const conversationResponse = await createConversation(userId, roleId, 'role', '信息采集对话');
          if (conversationResponse && conversationResponse.data && conversationResponse.data.conversation_id) {
            const convId = conversationResponse.data.conversation_id;
            setConversationId(convId);
            setRoleId(roleId);
            console.log('会话记录创建成功');
            
            // 2. 保存初始AI消息
            try {
              await createMessage(
                convId,
                roleId,  // 发送者：角色ID（AI）
                userId,  // 接收者：用户ID
                questionTemplates[1].text,  // 初始消息内容
                'text'
              );
              console.log('初始消息保存成功');
            } catch (msgError) {
              console.error('保存初始消息失败:', msgError);
              // 不阻止流程，静默失败
            }
          }
        } else {
          console.warn('无法获取角色信息，跳过创建会话记录');
        }
      } catch (error) {
        console.error('创建会话记录失败:', error);
        // 不阻止界面显示，静默失败
      }
    };
    
    if (userId) {
      initConversation();
    }
  }, [userId]);

  // 自动滚动到底部
  useEffect(() => {
    if (messages.length > 0 && flatListRef.current) {
      const timer = setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages.length]);


  const handleSend = async () => {
    if (!inputText.trim() || loading) return;

    const userAnswer = inputText.trim();
    const userMessage = {
      id: Date.now().toString(),
      text: userAnswer,
      sender: 'user',
      timestamp: new Date(),
    };

    // 保存用户回答
    const updatedAnswers = { ...userAnswers, [currentQuestion]: userAnswer };
    setUserAnswers(updatedAnswers);

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);
    setIsTyping(true);

    try {
      // 先保存用户的真实回答到数据库
      if (conversationId && roleId) {
        try {
          await createMessage(
            conversationId,
            userId,  // 发送者：用户ID
            roleId,  // 接收者：角色ID
            userAnswer,  // 用户的真实回答
            'text'
          );
          console.log('用户回答保存成功');
        } catch (msgError) {
          console.error('保存用户回答失败:', msgError);
          // 不阻止流程，静默失败
        }
      }

      // 根据当前问题序号，暂存数据到前端状态
      if (currentQuestion === 1) {
        // 第一个问题：暂存职业
        setTempData(prev => ({
          ...prev,
          description: `职业：${userAnswer}`
        }));
      } else if (currentQuestion === 2) {
        // 第二个问题：合并职业和喜好
        const jobAnswer = updatedAnswers[1] || '';
        setTempData(prev => ({
          ...prev,
          description: `职业：${jobAnswer}；喜好：${userAnswer}`
        }));
      }

      // 检查是否已回答了所有5个问题（包括当前回答）
      const answeredCount = Object.keys(updatedAnswers).length;
      const isLastQuestion = currentQuestion === 5 || answeredCount >= 5;
      
      // 如果还有下一个问题，让AI生成下一个问题
      if (!isLastQuestion) {
        const nextQuestion = currentQuestion + 1;
        // 后端系统prompt已包含格式要求，前端只需发送简单指令
        const response = await sendInfoCollectionLLM(`请根据之前的对话内容，生成第${nextQuestion}个问题。`, userId);
        
        const nextQuestionText = response.data?.answer || response.answer || getFallbackQuestion(nextQuestion, updatedAnswers);
        const nextQuestionMessage = {
          id: (Date.now() + 1).toString(),
          text: nextQuestionText,
          sender: 'ai',
          timestamp: new Date(),
        };
        
        setMessages(prev => [...prev, nextQuestionMessage]);
        setCurrentQuestion(nextQuestion);
        
        // 当第4个问题返回结果（生成第5个问题）时，就更新界面
        if (nextQuestion === 5) {
          setIsCompleted(true);
        }
      } else {
        // 最后一个问题，生成总结
        // 后端系统prompt已包含格式要求，前端只需发送简单指令
        const response = await sendInfoCollectionLLM('请根据之前的对话内容，生成总结性的回复。', userId);
        
        const summaryText = response.data?.answer || response.answer || getFallbackSummary(updatedAnswers);
        const summaryMessage = {
          id: (Date.now() + 1).toString(),
          text: summaryText,
          sender: 'ai',
          timestamp: new Date(),
        };
        
        setMessages(prev => [...prev, summaryMessage]);
        
        // 标记为已完成，显示"下一步"按钮
        // useEffect 也会检测并更新，这里确保立即更新
        setIsCompleted(true);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        text: '抱歉，网络连接出现问题，请稍后再试。',
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  };

  // 获取备用问题（当AI生成失败时使用）
  const getFallbackQuestion = (questionNum, allAnswers) => {
    if (questionNum === 2 && allAnswers[1]) {
      // 问题2：需要包含职业信息
      return `${allAnswers[1]}..${allAnswers[1]}.,除了工作之外，"我"还喜欢做些什么？`;
    } else if (questionNum === 3 && allAnswers[2]) {
      // 问题3：需要包含喜好和性格推测
      return `原来"我"喜欢这些呀--${allAnswers[2]}\n嗯，如果要猜的话，我觉得"我"的性格类型也许是ISFP--艺术家型。\n这是"我"的模样`;
    } else if (questionNum === 4) {
      // 问题4：先回应，然后提问
      const answer3 = allAnswers[3] || '';
      return `嗯，看来这个性格类型确实很符合"我"呢。\n我能感受到"我"的罗阔被稳定宇现实感包裹着。那现在告诉我吧--最近"我"都在忙些什么呢？`;
    }
    // 问题1不应该调用此函数（因为问题1是硬编码的），但为了安全起见返回空字符串
    return '';
  };

  // 获取备用总结（当AI生成失败时使用）
  const getFallbackSummary = (allAnswers) => {
    const work = allAnswers[1] || '未知职业';
    const hobby = allAnswers[2] || '未知喜好';
    const recent = allAnswers[4] || '未知';
    
    return `谢谢你告诉我这些，现在我的形象清晰的多了。\n你的记忆开始在我体内沉淀，我能感到一种平衡--${work}和${hobby}。\n从你赋予我的一切里，我看见了这样的"我"：职业是${work}，喜欢${hobby}，最近在${recent}。\n这就是现在的"我"，被你一步步描述出来的形状。我能感到一种安定的真实，这种感觉......就是"活着"。`;
  };

  // 生成system_prompt的函数
  const buildSystemPrompt = (loadName, roleName, description) => {
    const roleNameText = roleName || '{{role}}';
    const descriptionText = description || '{{responsibility}}';
    return `你是${loadName}的"第二自我"，这是由${loadName}创建的个性化AI。你作为${loadName}的代表，代表${loadName}与他人互动。目前，你正在以${roleNameText}的角色与外部用户互动。你的职责是${descriptionText}。`;
  };

  const handleSkip = async () => {
    // 跳过信息采集，提交暂存的数据，然后跳转到主界面
    try {
      if (tempData.description) {
        // 获取用户信息和角色信息，用于生成system_prompt
        let loadName = '';
        let roleName = '';
        
        try {
          // 获取用户信息（loads.name）
          const loadResponse = await getUserById(userId);
          if (loadResponse && loadResponse.data) {
            loadName = loadResponse.data.name || '';
          }
          
          // 获取角色信息（roles.name）
          const roleResponse = await getRoleByUuid(userId);
          if (roleResponse && roleResponse.data) {
            roleName = roleResponse.data.name || '';
          }
        } catch (error) {
          console.error('获取用户或角色信息失败:', error);
          // 如果获取失败，使用userInfo中的信息
          if (userInfo) {
            loadName = userInfo.name || '';
            roleName = userInfo.name || ''; // 如果roles.name没有，使用loads.name
          }
        }
        
        // 生成system_prompt
        const systemPrompt = buildSystemPrompt(loadName, roleName, tempData.description);
        
        // 提交数据（包含前端生成的system_prompt）
        await submitInfoCollection(userId, {
          ...tempData,
          system_prompt: systemPrompt
        });
        console.log('信息采集数据已提交');
      }
    } catch (error) {
      console.error('提交信息采集数据失败:', error);
      // 即使失败也继续跳转
    }
    router.replace('/home');
  };

  const handleNext = async () => {
    // 完成信息采集，提交暂存的数据，然后跳转到主界面
    try {
      if (tempData.description) {
        // 获取用户信息和角色信息，用于生成system_prompt
        let loadName = '';
        let roleName = '';
        
        try {
          // 获取用户信息（loads.name）
          const loadResponse = await getUserById(userId);
          if (loadResponse && loadResponse.data) {
            loadName = loadResponse.data.name || '';
          }
          
          // 获取角色信息（roles.name）
          const roleResponse = await getRoleByUuid(userId);
          if (roleResponse && roleResponse.data) {
            roleName = roleResponse.data.name || '';
          }
        } catch (error) {
          console.error('获取用户或角色信息失败:', error);
          // 如果获取失败，使用userInfo中的信息
          if (userInfo) {
            loadName = userInfo.name || '';
            roleName = userInfo.name || ''; // 如果roles.name没有，使用loads.name
          }
        }
        
        // 生成system_prompt
        const systemPrompt = buildSystemPrompt(loadName, roleName, tempData.description);
        
        // 提交数据（包含前端生成的system_prompt）
        await submitInfoCollection(userId, {
          ...tempData,
          system_prompt: systemPrompt
        });
        console.log('信息采集数据已提交');
      }
    } catch (error) {
      console.error('提交信息采集数据失败:', error);
      // 即使失败也继续跳转
    }
    router.replace('/home');
  };

  const renderMessage = ({ item }) => (
    <View style={[
      styles.messageContainer,
      item.sender === 'user' ? styles.userMessageContainer : styles.aiMessageContainer
    ]}>
      <View style={[
        styles.messageBubble,
        item.sender === 'user' ? styles.userBubble : styles.aiBubble
      ]}>
        <Text style={[
          styles.messageText,
          item.sender === 'user' ? styles.userText : styles.aiText
        ]}>
          {item.text}
        </Text>
      </View>
    </View>
  );

  return (
    <LinearGradient
      colors={['#FFE5F0', '#E5F0FF', '#D6E8FF']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="dark-content" />
      
      {/* 顶部操作栏 */}
      <View style={styles.topBar}>
        <View style={styles.progressContainer}>
          <Text style={styles.progressText}>
            {Math.min(currentQuestion, 4)}/4
          </Text>
        </View>
        {/* {!isCompleted && (
          <TouchableOpacity onPress={handleSkip} style={styles.skipButton}>
            <Text style={styles.skipText}>跳过</Text>
          </TouchableOpacity>
        )} */}
      </View>

      {/* 消息列表 */}
      <View style={styles.chatContainer}>
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          style={styles.flatList}
        />
      </View>

      {/* 输入区域或下一步按钮 - 固定在底部 */}
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 20 : 40}
      >
        {isCompleted ? (
          <View style={styles.inputContainer}>
            <TouchableOpacity 
              style={styles.nextStepButton}
              onPress={handleNext}
              activeOpacity={0.8}
            >
              <Text style={styles.nextStepText}>下一步</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.inputContainer}>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                value={inputText}
                onChangeText={setInputText}
                placeholder="塑造你的第二自我..."
                placeholderTextColor="rgba(0, 0, 0, 0.4)"
                multiline
                maxLength={500}
                onFocus={() => setIsInputFocused(true)}
                onBlur={() => setIsInputFocused(false)}
              />
              {/* 根据输入框状态和内容显示发送按钮或语音按钮 */}
              {(isInputFocused || inputText.trim()) ? (
                <TouchableOpacity 
                  style={[styles.actionButton, (!inputText.trim() || loading) && styles.actionButtonDisabled]}
                  onPress={handleSend}
                  disabled={!inputText.trim() || loading}
                >
                  {loading ? (
                    <ActivityIndicator size="small" color="#FF6B9D" />
                  ) : (
                    <Text style={styles.sendIcon}>📤</Text>
                  )}
                </TouchableOpacity>
              ) : (
                <TouchableOpacity 
                  style={styles.actionButton}
                  onPress={() => {
                    // TODO: 实现语音输入功能
                    console.log('Voice input');
                  }}
                >
                  <Text style={styles.micIcon}>🎤</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
  },
  progressContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressText: {
    color: '#333333',
    fontSize: 16,
    fontWeight: '500',
  },
  skipButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  skipText: {
    color: '#FF6B9D',
    fontSize: 14,
  },
  chatContainer: {
    flex: 1,
  },
  flatList: {
    flex: 1,
  },
  messageList: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  messageContainer: {
    marginBottom: 15,
    width: '100%',
  },
  userMessageContainer: {
    alignItems: 'flex-end',
  },
  aiMessageContainer: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderBottomRightRadius: 5,
    maxWidth: '75%',
  },
  aiBubble: {
    backgroundColor: '#FFFFFF',
    borderBottomLeftRadius: 5,
    maxWidth: '95%',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#FF6B9D',
  },
  aiText: {
    color: '#333333',
  },
  inputContainer: {
    paddingHorizontal: 20,
    paddingBottom: Platform.OS === 'ios' ? 20 : 10,
    paddingTop: 10,
    backgroundColor: 'transparent',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
  },
  input: {
    flex: 1,
    color: '#333333',
    fontSize: 16,
    maxHeight: 100,
    paddingRight: 10,
  },
  actionButton: {
    padding: 8,
    minWidth: 36,
    minHeight: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionButtonDisabled: {
    opacity: 0.5,
  },
  micIcon: {
    fontSize: 20,
  },
  sendIcon: {
    fontSize: 20,
  },
  nextStepButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextStepText: {
    color: '#FF6B9D',
    fontSize: 16,
    fontWeight: '600',
  },
});

