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
        const rawRedirectPath = route.query.redirect || '/assets';
        const redirectPath = typeof rawRedirectPath === 'string' &&
          rawRedirectPath.startsWith('/') &&
          !rawRedirectPath.startsWith('//')
          ? rawRedirectPath
          : '/assets';
        // 強制刷新頁面並跳轉到登入前目標頁面
        window.location.href = redirectPath;
      } else {
        // 如果沒有 token，跳回首頁
        window.location.href = '/';
      }
    });

    return {};
  },
};
</script>
