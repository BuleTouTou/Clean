import { createApp } from "vue";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import { createRouter, createWebHistory } from "vue-router";
import { routes } from "vue-router/auto-routes";
import App from "./App.vue";
import "./styles/tailwind.css";

const app = createApp(App);
app.use(VueQueryPlugin, { queryClient: new QueryClient() });
app.use(createRouter({ history: createWebHistory(), routes }));
app.mount("#app");
