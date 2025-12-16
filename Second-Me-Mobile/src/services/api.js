import axios from 'axios';
import { Platform } from 'react-native';

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

export default api;
