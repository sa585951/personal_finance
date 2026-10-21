<template>
  <div>正在登入，請稍候...</div>
</template>

<script>
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '@/api';
import { safeRedirectPath } from '@/utils/authNavigation';

export default {
  name: 'AuthCallback',
  setup() {
    const route = useRoute();

    onMounted(async () => {
      const redirectPath = safeRedirectPath(route.query.redirect, '/assets');
      // Immediately erase legacy query tokens from this history entry.
      window.history.replaceState({}, '', '/auth-callback');
      localStorage.removeItem('authToken');
      try {
        const response = await apiClient.get('/api/auth/me');
        if (!response.data?.success) throw new Error('No cookie session');
        window.location.replace(redirectPath);
      } catch {
        window.location.replace(`/login?redirect=${encodeURIComponent(redirectPath)}`);
      }
    });

    return {};
  },
};
</script>
