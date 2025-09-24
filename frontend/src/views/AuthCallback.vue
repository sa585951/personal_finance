<template>
  <div>正在登入，請稍候...</div>
</template>

<script>
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';

export default {
  name: 'AuthCallback',
  setup() {
    const route = useRoute();

    onMounted(() => {
      const token = route.query.token;
      if (token) {
        // 將 token 存到瀏覽器的 localStorage
        localStorage.setItem('authToken', token);
        // 強制刷新頁面並跳轉到資產總覽頁面
        window.location.href = '/assets'; 
      } else {
        // 如果沒有 token，跳回首頁
        window.location.href = '/';
      }
    });

    return {};
  },
};
</script>