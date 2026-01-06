import { createContext, useContext, useState, useEffect } from 'react';

// 安全导入 AsyncStorage
let AsyncStorage;
try {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
} catch (error) {
  // 如果 AsyncStorage 不可用，使用内存存储作为后备
  console.warn('AsyncStorage 不可用，使用内存存储（应用重启后数据会丢失）');
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

const UserContext = createContext();

const USER_STORAGE_KEY = '@user_id';
const USER_INFO_STORAGE_KEY = '@user_info';

export const UserProvider = ({ children }) => {
  const [userId, setUserId] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // 应用启动时从AsyncStorage恢复用户信息
  useEffect(() => {
    loadUserFromStorage();
  }, []);

  const loadUserFromStorage = async () => {
    try {
      const storedUserId = await AsyncStorage.getItem(USER_STORAGE_KEY);
      const storedUserInfo = await AsyncStorage.getItem(USER_INFO_STORAGE_KEY);
      
      if (storedUserId) {
        setUserId(storedUserId);
        if (storedUserInfo) {
          try {
            setUserInfo(JSON.parse(storedUserInfo));
          } catch (e) {
            console.error('解析用户信息失败:', e);
          }
        }
      }
    } catch (error) {
      console.error('从存储加载用户信息失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 登录：保存用户ID和信息
  const login = async (id, info = null) => {
    try {
      // 确保 id 是字符串类型（AsyncStorage 在 Android 上要求字符串）
      const userIdString = String(id);
      await AsyncStorage.setItem(USER_STORAGE_KEY, userIdString);
      setUserId(userIdString);
      
      if (info) {
        await AsyncStorage.setItem(USER_INFO_STORAGE_KEY, JSON.stringify(info));
        setUserInfo(info);
      }
    } catch (error) {
      console.error('保存用户信息失败:', error);
      throw error;
    }
  };

  // 登出：清除用户信息
  const logout = async () => {
    try {
      await AsyncStorage.removeItem(USER_STORAGE_KEY);
      await AsyncStorage.removeItem(USER_INFO_STORAGE_KEY);
      setUserId(null);
      setUserInfo(null);
    } catch (error) {
      console.error('清除用户信息失败:', error);
      throw error;
    }
  };

  // 更新用户信息
  const updateUserInfo = async (info) => {
    try {
      await AsyncStorage.setItem(USER_INFO_STORAGE_KEY, JSON.stringify(info));
      setUserInfo(info);
    } catch (error) {
      console.error('更新用户信息失败:', error);
      throw error;
    }
  };

  const value = {
    userId,
    userInfo,
    isLoading,
    login,
    logout,
    updateUserInfo,
    isLoggedIn: !!userId,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};

// Hook：在组件中使用用户信息
export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

