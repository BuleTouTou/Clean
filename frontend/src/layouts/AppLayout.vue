<script setup lang="ts">
import { computed, h } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import {
  NConfigProvider,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NMenu,
  NMessageProvider,
} from "naive-ui";
import type { GlobalThemeOverrides } from "naive-ui";

const route = useRoute();
const router = useRouter();
const menu = computed(() => (route.path.startsWith("/reports") ? "reports" : "task"));
const menuOptions = [
  { label: () => h(RouterLink, { to: "/" }, { default: () => "任务执行" }), key: "task" },
  { label: () => h(RouterLink, { to: "/reports" }, { default: () => "历史报告" }), key: "reports" },
];

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#6510ad",
    primaryColorHover: "#7623bd",
    primaryColorPressed: "#4f087f",
    primaryColorSuppl: "#8b45c7",
  },
};

function navigate(key: string) {
  router.push(key === "reports" ? "/reports" : "/");
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-layout has-sider class="h-screen w-full bg-slate-50">
        <n-layout-sider bordered :width="250" class="!bg-[#6510ad]">
          <div class="px-6 py-7 text-white">
            <div class="text-xl font-bold tracking-widest">房准</div>
            <div class="mt-2 text-xs text-slate-300">房源数据清洗平台</div>
          </div>
          <n-menu :value="menu" :options="menuOptions" inverted @update:value="navigate" />
          <div class="absolute bottom-5 px-6 text-xs leading-6 text-slate-300">清洗、审核、导出<br>全流程留痕</div>
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
