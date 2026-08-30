import { createApp } from "vue";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import App from "./App.vue";
import "./styles/tailwind.css";

const app = createApp(App);
app.use(VueQueryPlugin, { queryClient: new QueryClient() });
app.mount("#app");
