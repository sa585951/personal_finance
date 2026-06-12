<template>
  <div>{{ message }}</div>
</template>

<script>
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

export default {
  name: 'AuthCallback',
  setup() {
    const route = useRoute();
    const message = ref('正在登入，請稍候...');

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
      } else if (route.query.pwa_login === 'complete') {
        message.value = '登入已完成，請回到主畫面的 Nomica。';
      } else {
        // 如果沒有 token，跳回首頁
        window.location.href = '/';
      }
    });

    return { message };
  },
};
</script>
