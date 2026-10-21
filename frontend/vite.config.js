import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  if (command === 'build' && env.VITE_DEV_AUTH_BYPASS === 'true') {
    throw new Error('Release build must not enable VITE_DEV_AUTH_BYPASS');
  }
  const apiTarget = process.env.NOMICA_DEV_API_TARGET || 'http://127.0.0.1:5000';
  return {
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/line-login-": { target: apiTarget, changeOrigin: true },
    },
  },
  };
});
