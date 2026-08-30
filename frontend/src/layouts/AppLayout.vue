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

const route = useRoute();
const router = useRouter();
const menu = computed(() => (route.path.startsWith("/reports") ? "reports" : "task"));
const menuOptions = [
  { label: () => h(RouterLink, { to: "/" }, { default: () => "任务执行" }), key: "task" },
  { label: () => h(RouterLink, { to: "/reports" }, { default: () => "历史报告" }), key: "reports" },
];

function navigate(key: string) {
  router.push(key === "reports" ? "/reports" : "/");
}
</script>

<template>
  <n-config-provider>
    <n-message-provider>
      <n-layout has-sider class="min-h-screen bg-slate-50">
        <n-layout-sider bordered :width="250" class="!bg-[#183f63]">
          <div class="px-6 py-7 text-white">
            <div class="text-xl font-bold tracking-widest">房准</div>
            <div class="mt-2 text-xs text-slate-300">房源数据清洗平台</div>
          </div>
          <n-menu :value="menu" :options="menuOptions" inverted @update:value="navigate" />
          <div class="absolute bottom-5 px-6 text-xs leading-6 text-slate-300">清洗、审核、导出<br>全流程留痕</div>
        </n-layout-sider>
        <n-layout-content class="p-6 md:p-10">
          <div class="mx-auto max-w-6xl">
            <slot />
          </div>
        </n-layout-content>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>
