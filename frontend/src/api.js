import axios from 'axios';

// 建立一個 Axios 實例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL, // 從環境變數讀取 API 的基礎 URL
});

// 新增一個請求攔截器 (Request Interceptor)
apiClient.interceptors.request.use(
  (config) => {
    // 從 localStorage 獲取 token
    const token = localStorage.getItem('authToken');
    
    // 如果 token 存在，則在每個請求的 header 中加入 Authorization
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 只在開發模式下加入繞過 ngrok 警告的標頭
    if (import.meta.env.DEV) {
      config.headers['ngrok-skip-browser-warning'] = 'true';
    }
    
    return config;
  },
  (error) => {
    // 對請求錯誤做些什麼
    return Promise.reject(error);
  }
);

export default apiClient;
