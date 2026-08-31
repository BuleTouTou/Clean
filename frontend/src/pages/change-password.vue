<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { NAlert, NButton, NCard, NForm, NFormItem, NInput } from "naive-ui";
import { authState, changePassword } from "../auth";

const router = useRouter();
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  if (newPassword.value !== confirmPassword.value) {
    error.value = "两次输入的新密码不一致";
    return;
  }
  loading.value = true;
  try {
    await changePassword(currentPassword.value, newPassword.value);
    await router.replace("/");
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "密码修改失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
    <n-card class="w-full max-w-lg shadow-xl" title="首次登录，请修改密码">
      <p class="mb-5 text-sm text-slate-500">{{ authState.user?.name }}，设置新密码后才能进入系统。新密码至少 8 位。</p>
      <n-alert v-if="error" type="error" class="mb-5">{{ error }}</n-alert>
      <n-form @submit.prevent="submit">
        <n-form-item label="当前初始密码">
          <n-input v-model:value="currentPassword" type="password" show-password-on="click" autocomplete="current-password" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="newPassword" type="password" show-password-on="click" autocomplete="new-password" />
        </n-form-item>
        <n-form-item label="确认新密码">
          <n-input v-model:value="confirmPassword" type="password" show-password-on="click" autocomplete="new-password" @keyup.enter="submit" />
        </n-form-item>
        <n-button type="primary" block :loading="loading" :disabled="!currentPassword || newPassword.length < 8 || !confirmPassword" @click="submit">保存新密码并进入系统</n-button>
      </n-form>
    </n-card>
  </main>
</template>
