import { reactive } from "vue";
import { api, type UserInfo } from "./api";


export const authState = reactive<{ user: UserInfo | null; loaded: boolean }>({
  user: null,
  loaded: false,
});

export async function loadCurrentUser(force = false): Promise<UserInfo | null> {
  if (authState.loaded && !force) return authState.user;
  try {
    authState.user = (await api.me()).user;
  } catch {
    authState.user = null;
  } finally {
    authState.loaded = true;
  }
  return authState.user;
}

export async function login(username: string, password: string): Promise<UserInfo> {
  const user = (await api.login(username, password)).user;
  authState.user = user;
  authState.loaded = true;
  return user;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<UserInfo> {
  const user = (await api.changePassword(currentPassword, newPassword)).user;
  authState.user = user;
  authState.loaded = true;
  return user;
}

export async function logout(): Promise<void> {
  try {
    await api.logout();
  } finally {
    authState.user = null;
    authState.loaded = true;
  }
}
