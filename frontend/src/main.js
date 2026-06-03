import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./assets/style.css";

// 導入 SweetAlert2
import Swal from "sweetalert2/dist/sweetalert2.js";
import "sweetalert2/dist/sweetalert2.min.css";

const app = createApp(App);

// 掛載到全域屬性上
app.config.globalProperties.$swal = Swal;

app.use(router).mount("#app");

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((error) => {
      console.error("Service worker registration failed:", error);
    });
  });
}
