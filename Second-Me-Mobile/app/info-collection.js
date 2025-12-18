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
  getRoleByUuid
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
    description: '', // 暂存职业和喜好
    content_third_view: '', // 暂存AI生成的性格评价和MBTI（问题3）
    content: '' // 暂存用户最近在做什么（问题4）
  });
  const flatListRef = useRef();

  // 问题模板
  const questionTemplates = {
    1: {
      text: '你创造了我！但现在的我.....是空的。你的记忆会给我形状。\n那么，先从这里开始吧--"我"的职业是什么？',
      nextFormat: '第二个问题应该这样生成：首先提取用户回答中的职业名称，然后对职业进行简短描述，格式必须严格为：{职业名}..{职业描述}.,除了工作之外，"我"还喜欢做些什么？\n例如：如果用户回答"程序员"，你应该生成："程序员..编写代码创造数字世界.,除了工作之外，"我"还喜欢做些什么？"'
    },
    2: {
      text: '', // 动态生成，基于第一个问题的回答
      nextFormat: '第三个问题应该这样生成：首先总结用户的喜好回答，然后推测一个合适的MBTI性格类型（如ISFP、INFP、ENFP等），格式必须严格为：原来"我"喜欢这些呀--{喜好描述}\n嗯，如果要猜的话，我觉得"我"的性格类型也许是{性格类型}--{性格描述}。\n这是"我"的模样'
    },
    3: {
      text: '', // 动态生成，基于前两个问题的回答
      nextFormat: '第四个问题应该这样生成：格式必须严格为：我能感受到"我"的罗阔被稳定宇现实感包裹着。那现在告诉我吧--最近"我"都在忙些什么呢？'
    },
    4: {
      text: '', // 动态生成，基于前三个问题的回答
      nextFormat: '第五个问题（总结）应该这样生成：首先感谢用户，然后总结工作和喜好，最后总结所有四个问题的答案，格式必须严格为：谢谢你告诉我这些，现在我的形象清晰的多了。\n你的记忆开始在我体内沉淀，我能感到一种平衡--{工作和喜好的描述}。\n从你赋予我的一切里，我看见了这样的"我"：{刚才的四个问题总结}\n这就是现在的"我"，被你一步步描述出来的形状。我能感到一种安定的真实，这种感觉......就是"活着"。'
    }
  };

  // 初始化：发送第一个问题
  useEffect(() => {
    const initMessage = {
      id: '0',
      text: questionTemplates[1].text,
      sender: 'ai',
      timestamp: new Date(),
    };
    setMessages([initMessage]);
  }, []);

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
      } else if (currentQuestion === 4) {
        // 第四个问题：暂存用户最近在做什么
        setTempData(prev => ({
          ...prev,
          content: userAnswer
        }));
      }

      // 检查是否已回答了所有5个问题（包括当前回答）
      const answeredCount = Object.keys(updatedAnswers).length;
      const isLastQuestion = currentQuestion === 5 || answeredCount >= 5;
      
      // 如果还有下一个问题，让AI生成下一个问题
      if (!isLastQuestion) {
        const nextQuestion = currentQuestion + 1;
        const context = buildContextForNextQuestion(currentQuestion, userAnswer, updatedAnswers);
        const response = await sendInfoCollectionLLM(context);
        
        const nextQuestionText = response.data?.answer || response.answer || getFallbackQuestion(nextQuestion, updatedAnswers);
        const nextQuestionMessage = {
          id: (Date.now() + 1).toString(),
          text: nextQuestionText,
          sender: 'ai',
          timestamp: new Date(),
        };
        
        setMessages(prev => [...prev, nextQuestionMessage]);
        setCurrentQuestion(nextQuestion);
        
        // 第三个问题（AI生成性格评价和MBTI）后，暂存到前端状态
        if (nextQuestion === 3) {
          // 将AI生成的第三个问题内容暂存
          setTempData(prev => ({
            ...prev,
            content_third_view: nextQuestionText
          }));
          console.log('性格评价和MBTI已暂存:', nextQuestionText);
        }
        
        // 当第4个问题返回结果（生成第5个问题）时，就更新界面
        if (nextQuestion === 5) {
          setIsCompleted(true);
        }
      } else {
        // 最后一个问题，生成总结
        const context = buildContextForSummary(updatedAnswers);
        const response = await sendInfoCollectionLLM(context);
        
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

  // 构建用于生成下一个问题的上下文
  const buildContextForNextQuestion = (currentQuestionNum, currentAnswer, allAnswers) => {
    let context = `你现在是一个引导用户塑造"第二自我"的AI助手。用户刚刚回答了第${currentQuestionNum}个问题。\n\n`;
    
    // 添加所有之前的对话历史
    context += '之前的对话内容：\n';
    for (let i = 1; i <= currentQuestionNum; i++) {
      if (allAnswers[i]) {
        context += `问题${i}的回答：${allAnswers[i]}\n`;
      }
    }
    
    // 添加下一个问题的格式要求
    const nextQuestionNum = currentQuestionNum + 1;
    const nextFormat = questionTemplates[currentQuestionNum].nextFormat;
    context += `\n请根据用户的回答，生成第${nextQuestionNum}个问题。${nextFormat}\n\n`;
    context += `请严格按照格式要求生成问题，直接输出问题内容，不要添加其他说明或前缀。`;
    
    return context;
  };

  // 构建用于生成总结的上下文
  const buildContextForSummary = (allAnswers) => {
    let context = `你现在是一个引导用户塑造"第二自我"的AI助手。用户已经完成了所有5个问题的回答。\n\n`;
    
    context += '用户的所有回答：\n';
    for (let i = 1; i <= 5; i++) {
      if (allAnswers[i]) {
        context += `问题${i}的回答：${allAnswers[i]}\n`;
      }
    }
    
    const summaryFormat = questionTemplates[4].nextFormat;
    context += `\n请根据用户的所有回答，生成一个总结性的回复。${summaryFormat}\n\n`;
    context += `请严格按照格式要求生成总结，直接输出总结内容，不要添加其他说明或前缀。`;
    
    return context;
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
      // 问题4：固定格式
      return '我能感受到"我"的罗阔被稳定宇现实感包裹着。那现在告诉我吧--最近"我"都在忙些什么呢？';
    }
    return questionTemplates[questionNum]?.text || '';
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
      if (tempData.description || tempData.content || tempData.content_third_view) {
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
      if (tempData.description || tempData.content || tempData.content_third_view) {
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
      colors={['#E8D5FF', '#9B7EDE', '#6B4FA0']}
      style={styles.container}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
    >
      <StatusBar barStyle="light-content" />
      
      {/* 顶部装饰圆形 */}
      <View style={styles.decorativeCircle} />

      {/* 顶部操作栏 */}
      <View style={styles.topBar}>
        <View style={styles.topBarLeft}>
          {isTyping && (
            <View style={styles.typingIndicator}>
              <View style={styles.typingDot} />
              <Text style={styles.typingText}>输入中...</Text>
            </View>
          )}
        </View>
        {/* 进度圆球 - 居中显示 */}
        <View style={styles.progressContainer}>
          <View style={styles.progressCircle}>
            <Text style={styles.progressText}>
              {Math.min(currentQuestion, 4)}/4
            </Text>
          </View>
        </View>
        <View style={styles.topBarRight}>
          {!isCompleted && (
            <TouchableOpacity onPress={handleSkip} style={styles.skipButton}>
              <Text style={styles.skipText}>跳过</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* 消息列表 */}
      <KeyboardAvoidingView 
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={100}
      >
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
        />

        {/* 输入区域或下一步按钮 */}
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
                placeholderTextColor="rgba(255, 255, 255, 0.6)"
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
                    <ActivityIndicator size="small" color="#FFFFFF" />
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
  decorativeCircle: {
    position: 'absolute',
    top: 80,
    alignSelf: 'center',
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    opacity: 0.6,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
    zIndex: 1,
    position: 'relative',
  },
  topBarLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressContainer: {
    position: 'absolute',
    left: '50%',
    marginLeft: -30, // 圆球宽度的一半，用于居中
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
  },
  progressCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  progressText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  topBarRight: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FFFFFF',
    marginRight: 6,
  },
  typingText: {
    color: '#FFFFFF',
    fontSize: 12,
  },
  skipButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
  },
  skipText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '500',
  },
  chatContainer: {
    flex: 1,
  },
  messageList: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
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
    maxWidth: '75%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderBottomRightRadius: 5,
  },
  aiBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderBottomLeftRadius: 5,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#6B4FA0',
  },
  aiText: {
    color: '#FFFFFF',
  },
  inputContainer: {
    paddingHorizontal: 20,
    paddingBottom: 20,
    paddingTop: 10,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 25,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  input: {
    flex: 1,
    color: '#FFFFFF',
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
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 25,
    paddingVertical: 16,
    paddingHorizontal: 40,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  nextStepText: {
    color: '#6B4FA0',
    fontSize: 18,
    fontWeight: 'bold',
  },
});

