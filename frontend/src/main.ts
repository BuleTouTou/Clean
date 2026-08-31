import { createApp } from "vue";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import { createRouter, createWebHistory } from "vue-router";
import { routes } from "vue-router/auto-routes";
import App from "./App.vue";
import { authState, loadCurrentUser } from "./auth";
import "./assets/tailwind.css";

const app = createApp(App);
const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  const user = await loadCurrentUser();
  if (!user && to.path !== "/login") return "/login";
  if (!user) return true;
  if (user.mustChangePassword && to.path !== "/change-password") return "/change-password";
  if (!user.mustChangePassword && to.path === "/change-password") return "/";
  if (to.path === "/login") return user.mustChangePassword ? "/change-password" : "/";
  if (to.path.startsWith("/users") && authState.user?.role !== "admin") return "/";
  return true;
});

app.use(VueQueryPlugin, { queryClient: new QueryClient() });
app.use(router);
app.mount("#app");
