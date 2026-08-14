<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { useWatermark } from '@vben/hooks';
import { BasicLayout, LockScreen, UserDropdown } from '@vben/layouts';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';

import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const { destroyWatermark, updateWatermark } = useWatermark();

const menus = computed(() => []);
const AUTO_LOCK_IDLE_MS = 60 * 60 * 1000;

let autoLockTimer: null | number = null;

function clearAutoLockTimer() {
  if (autoLockTimer !== null) {
    window.clearTimeout(autoLockTimer);
    autoLockTimer = null;
  }
}

function triggerAutoLock() {
  if (accessStore.isLockScreen || accessStore.loginExpired) {
    return;
  }
  const password = accessStore.lockScreenPassword;
  if (!password) {
    return;
  }
  accessStore.lockScreen(password);
}

function resetAutoLockTimer() {
  clearAutoLockTimer();
  if (accessStore.isLockScreen || accessStore.loginExpired) {
    return;
  }
  autoLockTimer = window.setTimeout(() => {
    triggerAutoLock();
  }, AUTO_LOCK_IDLE_MS);
}

function handleUserActivity() {
  resetAutoLockTimer();
}

const autoLockEvents: Array<keyof WindowEventMap> = [
  'click',
  'keydown',
  'mousemove',
  'mousedown',
  'scroll',
  'touchstart',
];

const avatar = computed(() => {
  return userStore.userInfo?.avatar ?? preferences.app.defaultAvatar;
});

async function handleLogout() {
  await authStore.logout(false);
}

watch(
  () => ({
    enable: preferences.app.watermark,
    content: preferences.app.watermarkContent,
  }),
  async ({ enable, content }) => {
    if (enable) {
      await updateWatermark({
        content:
          content ||
          `${userStore.userInfo?.username} - ${userStore.userInfo?.realName}`,
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);

watch(
  () => [
    accessStore.isLockScreen,
    accessStore.loginExpired,
    accessStore.lockScreenPassword,
  ],
  () => {
    resetAutoLockTimer();
  },
  { immediate: true },
);

onMounted(() => {
  for (const eventName of autoLockEvents) {
    window.addEventListener(eventName, handleUserActivity, { passive: true });
  }
  resetAutoLockTimer();
});

onBeforeUnmount(() => {
  clearAutoLockTimer();
  for (const eventName of autoLockEvents) {
    window.removeEventListener(eventName, handleUserActivity);
  }
});
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.realName"
        description="Telegram Bot Console"
        tag-text="Admin"
        @logout="handleLogout"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
