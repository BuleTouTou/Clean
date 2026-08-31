<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { NAlert, NButton, NCard, NForm, NFormItem, NInput } from "naive-ui";
import { login } from "../auth";

const router = useRouter();
const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const user = await login(username.value, password.value);
    await router.replace(user.mustChangePassword ? "/change-password" : "/");
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#6510ad] to-[#2f0b55] px-4">
    <n-card class="w-full max-w-md shadow-2xl" :bordered="false">
      <div class="mb-8 text-center">
        <div class="text-3xl font-bold tracking-widest text-[#6510ad]">房准</div>
        <h1 class="mt-4 text-xl font-semibold text-slate-800">房源数据清洗平台</h1>
        <p class="mt-2 text-sm text-slate-500">请使用管理员分配的账号登录</p>
      </div>
      <n-alert v-if="error" type="error" class="mb-5">{{ error }}</n-alert>
      <n-form @submit.prevent="submit">
        <n-form-item label="账号">
          <n-input v-model:value="username" size="large" autocomplete="username" placeholder="请输入账号" @keyup.enter="submit" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="password" type="password" show-password-on="click" size="large" autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submit" />
        </n-form-item>
        <n-button type="primary" size="large" block :loading="loading" :disabled="!username || !password" @click="submit">登录</n-button>
      </n-form>
    </n-card>
  </main>
</template>
