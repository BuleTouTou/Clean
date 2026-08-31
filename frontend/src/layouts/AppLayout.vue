<script setup lang="ts">
import { computed, h } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import {
  NButton,
  NConfigProvider,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NMenu,
  NMessageProvider,
} from "naive-ui";
import type { GlobalThemeOverrides } from "naive-ui";
import { authState, logout } from "../auth";

const route = useRoute();
const router = useRouter();
const publicPage = computed(() => ["/login", "/change-password"].includes(route.path));
const menu = computed(() => route.path.startsWith("/users") ? "users" : route.path.startsWith("/reports") ? "reports" : "task");
const menuOptions = computed(() => [
  { label: () => h(RouterLink, { to: "/" }, { default: () => "任务执行" }), key: "task" },
  { label: () => h(RouterLink, { to: "/reports" }, { default: () => "历史报告" }), key: "reports" },
  ...(authState.user?.role === "admin"
    ? [{ label: () => h(RouterLink, { to: "/users" }, { default: () => "用户管理" }), key: "users" }]
    : []),
]);

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#6510ad",
    primaryColorHover: "#7623bd",
    primaryColorPressed: "#4f087f",
    primaryColorSuppl: "#8b45c7",
  },
};

function navigate(key: string) {
  router.push(key === "reports" ? "/reports" : key === "users" ? "/users" : "/");
}

async function signOut() {
  await logout();
  await router.replace("/login");
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <div v-if="publicPage" class="min-h-screen bg-slate-50">
        <slot />
      </div>
      <n-layout v-else has-sider class="h-screen w-full bg-slate-50">
        <n-layout-sider bordered :width="250" class="!bg-[#6510ad]">
          <div class="px-6 py-7 text-white">
            <div class="text-xl font-bold tracking-widest">房准</div>
            <div class="mt-2 text-xs text-slate-300">房源数据清洗平台</div>
          </div>
          <n-menu :value="menu" :options="menuOptions" inverted @update:value="navigate" />
          <div class="absolute bottom-5 left-0 right-0 px-6 text-sm text-white">
            <div class="font-medium">{{ authState.user?.name }}</div>
            <div class="mb-3 mt-1 text-xs text-slate-300">{{ authState.user?.username }} · {{ authState.user?.role === "admin" ? "管理员" : "普通用户" }}</div>
            <n-button size="small" secondary block @click="signOut">退出登录</n-button>
          </div>
        </n-layout-sider>
        <n-layout-content class="min-h-0 min-w-0 flex-1 overflow-auto p-6 md:p-10">
          <div class="w-full max-w-none">
            <slot />
          </div>
        </n-layout-content>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>
