import axios from 'axios';
import { Platform } from 'react-native';

// 安全导入 AsyncStorage
let AsyncStorage;
try {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
} catch (error) {
  // 如果 AsyncStorage 不可用，使用内存存储作为后备
  const memoryStorage = {};
  AsyncStorage = {
    getItem: async (key) => Promise.resolve(memoryStorage[key] || null),
    setItem: async (key, value) => {
      memoryStorage[key] = value;
      return Promise.resolve();
    },
    removeItem: async (key) => {
      delete memoryStorage[key];
      return Promise.resolve();
    },
  };
}

// 后端 API 地址配置
// 后端运行在 0.0.0.0:8001，允许其他电脑访问
// 
// 配置说明：
// 1. Android 模拟器：使用 10.0.2.2（模拟器自动映射到宿主机 localhost）
// 2. Android 真机：需要使用你电脑的局域网 IP 地址（例如：192.168.1.100）
//    获取 IP 方法：Windows 运行 `ipconfig`，查找 "IPv4 地址"
//                  Mac/Linux 运行 `ifconfig` 或 `ip addr`
// 3. iOS 模拟器：使用 localhost
// 4. iOS 真机：需要使用你电脑的局域网 IP 地址
//
// 请根据你的运行环境修改下面的 IP 地址
// ⚠️ 重要：如果在真机上运行，必须设置为你电脑的局域网 IP 地址
// 如果为 null，则使用默认地址（仅适用于模拟器）
const YOUR_COMPUTER_IP = '100.84.194.66';  // 你的 WLAN IP 地址

// 根据平台和是否设置了 IP 来决定使用哪个地址
// 如果设置了 YOUR_COMPUTER_IP，则使用 IP（适用于真机和模拟器）
// 如果为 null，则使用默认地址（仅适用于模拟器）
const getBaseUrl = () => {
  if (Platform.OS === 'android') {
    // Android：如果设置了 IP 则使用 IP，否则使用 10.0.2.2（仅模拟器）
    return YOUR_COMPUTER_IP 
      ? `http://${YOUR_COMPUTER_IP}:8001/api`
      : 'http://10.0.2.2:8001/api';
  } else {
    // iOS：如果设置了 IP 则使用 IP，否则使用 localhost（仅模拟器）
    return YOUR_COMPUTER_IP
      ? `http://${YOUR_COMPUTER_IP}:8001/api`
      : 'http://localhost:8001/api';
  }
};

const BASE_URL = getBaseUrl();

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动在请求头中携带用户ID
api.interceptors.request.use(
  async (config) => {
    try {
      const userId = await AsyncStorage.getItem('@user_id');
      if (userId) {
        config.headers['X-User-ID'] = userId;
      }
    } catch (error) {
      console.error('获取用户ID失败:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', {
    uri: file.uri,
    name: file.name,
    type: file.mimeType || 'text/plain',
  });

  try {
    const response = await api.post('/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
};

// 发送聊天消息（使用新的聊天接口，需要role_id和历史消息）
export const sendChatMessage = async (query, roleId, historyMessages = []) => {
  try {
    // 构建消息列表
    const messages = [
      ...historyMessages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text
      })),
      {
        role: 'user',
        content: query
      }
    ];

    const response = await api.post('/chat', {
      messages: messages,
      metadata: {
        role_id: roleId,
        enable_l0_retrieval: true,
        enable_l1_retrieval: false
      },
      stream: false,
      temperature: 0.7,
      max_tokens: 2000
    });

    // 处理响应格式
    // 如果响应是 APIResponse 格式（有 code 和 data 字段）
    if (response.data && response.data.code !== undefined) {
      if (response.data.code !== 200) {
        throw new Error(response.data.message || '请求失败');
      }
      // 从 data 字段中提取响应
      const data = response.data.data;
      if (data && data.choices && data.choices.length > 0) {
        const answer = data.choices[0].message.content;
        return { answer };
      } else if (data && data.answer) {
        return { answer: data.answer };
      }
    }
    // 如果是直接的 OpenAI 格式响应
    else if (response.data && response.data.choices && response.data.choices.length > 0) {
      const answer = response.data.choices[0].message.content;
      return { answer };
    }
    // 兼容旧格式
    else if (response.data && response.data.data && response.data.data.answer) {
      return response.data.data;
    }
    
    throw new Error('无法解析响应');
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};

// 创建会话记录（用于信息采集界面初始化）
// 新接口：传入参与者ID列表和会话类型
export const createConversation = async (participantIds, conversationType = 'single', title = null) => {
  try {
    const response = await api.post('/conversations', {
      participant_ids: participantIds,  // 参与者ID列表（loads.id 或 roles.id 的列表）
      conversation_type: conversationType,  // 会话类型（'single' 单聊, 'group' 群聊）
      title: title
    });
    return response.data;
  } catch (error) {
    console.error('Create conversation error:', error);
    throw error;
  }
};

// 创建消息记录（新表结构：移除receiver_id，添加sender_type）
export const createMessage = async (conversationId, senderId, content, messageType = 'text', attachmentUrl = null, senderType = 'user') => {
  try {
    const response = await api.post('/messages', {
      conversation_id: conversationId,
      sender_id: senderId,
      content: content,
      message_type: messageType,
      attachment_url: attachmentUrl,
      sender_type: senderType  // 'user' 真实用户, 'ai' AI用户
    });
    return response.data;
  } catch (error) {
    console.error('Create message error:', error);
    throw error;
  }
};

// 信息采集过程中的LLM调用（不依赖role和system_prompt）
export const sendInfoCollectionLLM = async (query, load_id, conversation_id) => {
  try {
    if (!conversation_id) {
      throw new Error('conversation_id is required');
    }
    const response = await api.post('/info-collection/llm', { 
      query, 
      load_id, 
      conversation_id 
    });
    return response.data;
  } catch (error) {
    console.error('Info collection LLM error:', error);
    throw error;
  }
};

// 登录或创建用户（根据手机号）
export const loginOrCreateUser = async (user_mobile, name = null) => {
  try {
    const response = await api.post('/loads/login', {
      user_mobile,
      name
    });
    return response.data;
  } catch (error) {
    console.error('Login or create user error:', error);
    throw error;
  }
};

// 根据用户ID获取用户信息
export const getUserById = async (userId) => {
  try {
    const response = await api.get(`/loads/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Get user by id error:', error);
    throw error;
  }
};

// 根据用户ID更新用户信息
export const updateUserById = async (userId, userData) => {
  try {
    const response = await api.put(`/loads/${userId}`, userData);
    return response.data;
  } catch (error) {
    console.error('Update user error:', error);
    throw error;
  }
};

// 保留旧的 createUser 方法以兼容
export const createUser = async (name, email = '', description = null) => {
  try {
    const response = await api.post('/loads', {
      name,
      email,
      description,
      status: 'active'
    });
    return response.data;
  } catch (error) {
    console.error('Create user error:', error);
    throw error;
  }
};

export const getCurrentLoad = async () => {
  try {
    const response = await api.get('/loads/current');
    return response.data;
  } catch (error) {
    console.error('Get current load error:', error);
    throw error;
  }
};

export const storeLoadDescription = async (description) => {
  try {
    const response = await api.post('/loads/description', { description });
    return response.data;
  } catch (error) {
    console.error('Store load description error:', error);
    throw error;
  }
};

export const generateSystemPrompt = async () => {
  try {
    const response = await api.post('/loads/generate-system-prompt');
    return response.data;
  } catch (error) {
    console.error('Generate system prompt error:', error);
    throw error;
  }
};

export const updateRoleName = async (userId, name) => {
  try {
    // 使用 /roles/uuid/{uuid} 端点，因为 userId 是 loads.id (UUID)
    const response = await api.put(`/roles/uuid/${userId}`, { name });
    return response.data;
  } catch (error) {
    console.error('Update role name error:', error);
    throw error;
  }
};

export const storeL1BioContentThirdView = async (content_third_view) => {
  try {
    const response = await api.post('/l1-bios/content-third-view', { content_third_view });
    return response.data;
  } catch (error) {
    console.error('Store L1 bio content third view error:', error);
    throw error;
  }
};

export const storeStatusBioContent = async (content) => {
  try {
    const response = await api.post('/status-biography/content', { content });
    return response.data;
  } catch (error) {
    console.error('Store status bio content error:', error);
    throw error;
  }
};

export const storeStatusBioContentThirdView = async (content_third_view) => {
  try {
    const response = await api.post('/status-biography/content-third-view', { content_third_view });
    return response.data;
  } catch (error) {
    console.error('Store status bio content third view error:', error);
    throw error;
  }
};

export const getRoleByUuid = async (userId) => {
  try {
    const response = await api.get(`/roles/by-uuid/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Get role by uuid error:', error);
    throw error;
  }
};

// 根据会话ID获取消息列表
export const getMessagesByConversationId = async (conversationId, limit = null, offset = 0, orderByDesc = false) => {
  try {
    const params = new URLSearchParams();
    if (limit !== null) params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    params.append('order_by_desc', orderByDesc.toString());
    
    const response = await api.get(`/conversations/${conversationId}/messages?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Get messages by conversation id error:', error);
    throw error;
  }
};

// 获取用户的会话列表
export const getConversations = async (limit = null, offset = 0) => {
  try {
    const params = new URLSearchParams();
    if (limit !== null) params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    
    const response = await api.get(`/conversations?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Get conversations error:', error);
    throw error;
  }
};

export const submitInfoCollection = async (userId, data) => {
  try {
    const response = await api.post('/info-collection/submit', {
      description: data.description || '',
      system_prompt: data.system_prompt || ''
    });
    return response.data;
  } catch (error) {
    console.error('Submit info collection error:', error);
    throw error;
  }
};

export default api;
