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
// 后端运行在 0.0.0.0:8001，使用电脑的局域网 IP
// Android 模拟器使用 10.0.2.2 访问宿主机
// 真机使用电脑的局域网 IP 地址
const BASE_URL = Platform.OS === 'android' 
  ? 'http://100.84.194.66:8001/api'  // Android 真机或模拟器（已配置正确的 IP）
  : 'http://100.84.194.76:8003/api';

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

export const sendChatMessage = async (query) => {
  try {
    const response = await api.post('/chat', { query });
    return response.data;
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};

// 信息采集过程中的LLM调用（不依赖role和system_prompt）
export const sendInfoCollectionLLM = async (query) => {
  try {
    const response = await api.post('/info-collection/llm', { query });
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
    const response = await api.put(`/roles/${userId}`, { name });
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
    const response = await api.get(`/roles/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Get role by uuid error:', error);
    throw error;
  }
};

export const submitInfoCollection = async (userId, data) => {
  try {
    const response = await api.post('/info-collection/submit', {
      description: data.description || '',
      system_prompt: data.system_prompt || '',
      content: data.content || '',
      content_third_view: data.content_third_view || ''
    });
    return response.data;
  } catch (error) {
    console.error('Submit info collection error:', error);
    throw error;
  }
};

export default api;
