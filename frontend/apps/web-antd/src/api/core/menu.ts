import type { RouteRecordStringComponent } from '@vben/types';

import adminRoutes from '#/router/routes/modules/admin';

const routeComponentMap: Record<string, string> = {
  DashboardAnalytics: '/views/dashboard/analytics/index.vue',
  DashboardCloudAssetDetail: '/views/dashboard/cloud-assets/detail.vue',
  DashboardCloudAssets: '/views/dashboard/cloud-assets/index.vue',
  DashboardCloudAccounts: '/views/dashboard/settings/cloud-accounts.vue',
  DashboardCloudSyncJobDetail: '/views/dashboard/cloud-sync-jobs/detail.vue',
  DashboardCloudOrderDetail: '/views/dashboard/cloud-orders/detail.vue',
  DashboardCloudOrderRenewals: '/views/dashboard/tasks/auto-renew-detail.vue',
  DashboardCloudOrdersList: '/views/dashboard/cloud-orders/index.vue',
  DashboardCloudPlansList: '/views/dashboard/cloud-plans/index.vue',
  DashboardCloudPricing: '/views/dashboard/cloud-pricing/index.vue',
  DashboardLifecyclePlans: '/views/dashboard/tasks/plans.vue',
  DashboardMonitors: '/views/dashboard/monitors/index.vue',
  DashboardNoticePlans: '/views/dashboard/tasks/notices.vue',
  DashboardIpDeleteLogs: '/views/dashboard/ip-delete-logs/index.vue',
  DashboardOperationLogs: '/views/dashboard/operation-logs/index.vue',
  DashboardRechargeDetail: '/views/dashboard/recharges/detail.vue',
  DashboardRecharges: '/views/dashboard/recharges/index.vue',
  DashboardServerLogs: '/views/dashboard/server-logs/index.vue',
  DashboardServers: '/views/dashboard/servers/index.vue',
  DashboardServerStatistics: '/views/dashboard/server-statistics/index.vue',
  DashboardXrayNodes: '/views/dashboard/xray-nodes/index.vue',
  DashboardSettingsButtons: '/views/dashboard/settings/buttons.vue',
  DashboardSettingsCloudAccounts:
    '/views/dashboard/settings/cloud-accounts.vue',
  DashboardSettingsDatabase: '/views/dashboard/settings/database.vue',
  DashboardSettingsLifecycle: '/views/dashboard/settings/lifecycle.vue',
  DashboardSettingsLogs: '/views/dashboard/settings/logs.vue',
  DashboardSettingsNotifications: '/views/dashboard/settings/notifications.vue',
  DashboardSettingsPayment: '/views/dashboard/settings/payment.vue',
  DashboardSettingsSystem: '/views/dashboard/settings/system.vue',
  DashboardSettingsTexts: '/views/dashboard/settings/texts.vue',
  DashboardTasks: '/views/dashboard/tasks/index.vue',
  DashboardTelegramAccountList:
    '/views/dashboard/telegram-accounts/accounts.vue',
  DashboardTelegramChatRecords: '/views/dashboard/telegram-accounts/chats.vue',
  DashboardTelegramGroups: '/views/dashboard/telegram-accounts/groups.vue',
  DashboardAutoRenewTaskDetail: '/views/dashboard/tasks/auto-renew-detail.vue',
  DashboardUserBalanceDetails: '/views/dashboard/users/balance-details.vue',
  DashboardUsers: '/views/dashboard/users/index.vue',
};

function toMenuRoutes(routes: any[]): RouteRecordStringComponent[] {
  return routes.map((route) => {
    const routeName = String(route.name || '');
    const menuRoute: RouteRecordStringComponent = {
      ...route,
      component: route.children?.length
        ? 'BasicLayout'
        : routeComponentMap[routeName] || '/views/_core/fallback/not-found.vue',
    };

    if (route.children?.length) {
      menuRoute.children = toMenuRoutes(route.children);
    }

    return menuRoute;
  });
}

/**
 * 获取用户所有菜单
 */
export async function getAllMenusApi() {
  return toMenuRoutes(adminRoutes as any[]);
}
