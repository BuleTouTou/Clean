<script setup lang="ts">
import { ref } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { NAlert, NButton, NCard, NForm, NFormItem, NInput, NModal, NTag, useMessage } from "naive-ui";
import { api, type UserInfo } from "../../api";
import { formatBeijingTime } from "../../utils/datetime";

const message = useMessage();
const queryClient = useQueryClient();
const showCreate = ref(false);
const showReset = ref(false);
const selectedUser = ref<UserInfo | null>(null);
const username = ref("");
const name = ref("");
const initialPassword = ref("");
const resetPassword = ref("");

const usersQuery = useQuery({ queryKey: ["users"], queryFn: () => api.users() });
const createMutation = useMutation({ mutationFn: () => api.createUser(username.value, name.value, initialPassword.value) });
const resetMutation = useMutation({ mutationFn: () => api.resetUserPassword(selectedUser.value!.id, resetPassword.value) });

function openCreate() {
  username.value = "";
  name.value = "";
  initialPassword.value = "";
  showCreate.value = true;
}

function openReset(user: UserInfo) {
  selectedUser.value = user;
  resetPassword.value = "";
  showReset.value = true;
}

async function createAccount() {
  try {
    await createMutation.mutateAsync();
    showCreate.value = false;
    await queryClient.invalidateQueries({ queryKey: ["users"] });
    message.success("用户已创建，请将初始密码安全地交给用户");
  } catch (error) {
    message.error(error instanceof Error ? error.message : "创建失败");
  }
}

async function resetAccountPassword() {
  try {
    await resetMutation.mutateAsync();
    showReset.value = false;
    await queryClient.invalidateQueries({ queryKey: ["users"] });
    message.success("密码已重置，用户下次登录必须修改密码");
  } catch (error) {
    message.error(error instanceof Error ? error.message : "重置失败");
  }
}
</script>

<template>
  <div class="mb-8 flex items-center justify-between">
    <div>
      <div class="text-sm font-semibold uppercase tracking-widest text-tsinghua">用户管理</div>
      <h1 class="mt-2 text-3xl font-bold text-slate-800">系统用户</h1>
      <p class="mt-2 text-slate-500">分配普通用户账号和初始密码；用户首次登录必须修改密码。</p>
    </div>
    <n-button type="primary" @click="openCreate">创建用户</n-button>
  </div>

  <n-card class="shadow-sm">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead><tr class="border-b text-slate-500"><th class="p-3">ID</th><th class="p-3">账号</th><th class="p-3">姓名</th><th class="p-3">角色</th><th class="p-3">密码状态</th><th class="p-3">创建时间</th><th class="p-3">操作</th></tr></thead>
        <tbody>
          <tr v-for="user in usersQuery.data.value?.items ?? []" :key="user.id" class="border-b last:border-0">
            <td class="p-3 text-slate-500">{{ user.id }}</td>
            <td class="p-3 font-medium">{{ user.username }}</td>
            <td class="p-3">{{ user.name }}</td>
            <td class="p-3"><n-tag :type="user.role === 'admin' ? 'error' : 'info'" :bordered="false">{{ user.role === "admin" ? "管理员" : "普通用户" }}</n-tag></td>
            <td class="p-3"><n-tag :type="user.mustChangePassword ? 'warning' : 'success'" :bordered="false">{{ user.mustChangePassword ? "等待首次改密" : "正常" }}</n-tag></td>
            <td class="p-3 text-slate-500">{{ formatBeijingTime(user.createdAt) }}</td>
            <td class="p-3"><n-button v-if="user.role !== 'admin'" size="small" tertiary @click="openReset(user)">重置密码</n-button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </n-card>

  <n-modal v-model:show="showCreate" preset="card" title="创建普通用户" style="width: min(520px, calc(100vw - 32px))">
    <n-alert type="info" class="mb-4">初始密码只用于首次登录，用户登录后必须立即修改。</n-alert>
    <n-form>
      <n-form-item label="账号"><n-input v-model:value="username" placeholder="3–50 位字母、数字、点、下划线或短横线" /></n-form-item>
      <n-form-item label="姓名"><n-input v-model:value="name" placeholder="用户真实姓名" /></n-form-item>
      <n-form-item label="初始密码"><n-input v-model:value="initialPassword" type="password" show-password-on="click" placeholder="至少 8 位" /></n-form-item>
      <n-button type="primary" block :loading="createMutation.isPending.value" :disabled="!username || !name || initialPassword.length < 8" @click="createAccount">创建并分配账号</n-button>
    </n-form>
  </n-modal>

  <n-modal v-model:show="showReset" preset="card" title="重置用户密码" style="width: min(520px, calc(100vw - 32px))">
    <p class="mb-4 text-sm text-slate-500">正在重置 {{ selectedUser?.name }}（{{ selectedUser?.username }}）的密码。该用户现有登录会话将立即失效。</p>
    <n-form>
      <n-form-item label="新初始密码"><n-input v-model:value="resetPassword" type="password" show-password-on="click" placeholder="至少 8 位" /></n-form-item>
      <n-button type="primary" block :loading="resetMutation.isPending.value" :disabled="resetPassword.length < 8" @click="resetAccountPassword">确认重置</n-button>
    </n-form>
  </n-modal>
</template>
