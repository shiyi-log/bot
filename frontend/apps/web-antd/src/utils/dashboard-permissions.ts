import type { UserInfo } from '@vben/types';

import { computed } from 'vue';

import { useAccessStore, useUserStore } from '@vben/stores';

import { message } from 'ant-design-vue';

type DashboardUserInfo = UserInfo & {
  is_superuser?: boolean | string;
  permissions?: string[];
  roles?: string[];
};

function flagEnabled(value: unknown) {
  if (value === true) return true;
  if (typeof value === 'string') {
    return ['1', 'on', 'true', 'yes'].includes(value.toLowerCase());
  }
  return false;
}

export function useDashboardPermissions() {
  const accessStore = useAccessStore();
  const userStore = useUserStore();

  const userInfo = computed(
    () => userStore.userInfo as DashboardUserInfo | null,
  );
  const roles = computed(() => [
    ...(userInfo.value?.roles || []),
    ...(userStore.userRoles || []),
  ]);
  const permissions = computed(() => userInfo.value?.permissions || []);
  const accessCodes = computed(() => accessStore.accessCodes || []);
  const isSuperuser = computed(
    () =>
      flagEnabled(userInfo.value?.is_superuser) ||
      roles.value.includes('superuser') ||
      permissions.value.includes('superuser') ||
      accessCodes.value.includes('superuser'),
  );
  const canRunDangerousCloudAction = computed(() => isSuperuser.value);
  const canWriteFinance = computed(() => isSuperuser.value);

  function requireCloudDangerPermission(action = '执行高危云操作') {
    if (canRunDangerousCloudAction.value) return true;
    message.error(`${action}需要超级管理员权限`);
    return false;
  }

  return {
    canRunCloudDanger: canRunDangerousCloudAction,
    canRunDangerousCloudAction,
    canWriteFinance,
    isSuperuser,
    requireCloudDangerPermission,
  };
}
