import type { RouteRecordRaw } from 'vue-router';

import {
  Grid,
  MessageCircle,
  MessageSquareCode,
  MonitorSmartphone,
  Settings2,
  Users,
} from '@vben/icons';

const routes: RouteRecordRaw[] = [
  {
    meta: { icon: MessageCircle, order: -1, title: 'Telegram 管理' },
    name: 'TelegramBotConsole',
    path: '/admin',
    redirect: '/admin/telegram-users',
    children: [
      {
        name: 'TelegramUsers',
        path: 'telegram-users',
        component: () => import('#/views/telegram/users/index.vue'),
        meta: { icon: Users, title: '用户列表' },
      },
      {
        name: 'TelegramGroups',
        path: 'telegram-groups',
        component: () => import('#/views/telegram/groups/index.vue'),
        meta: { icon: MessageCircle, title: '群组列表' },
      },
      {
        name: 'TelegramGroupMembers',
        path: 'telegram-group-members',
        component: () => import('#/views/telegram/group-members/index.vue'),
        meta: { icon: Users, title: '群组成员' },
      },
      {
        name: 'TelegramBots',
        path: 'telegram-bots',
        component: () => import('#/views/telegram/bots/index.vue'),
        meta: { icon: MessageSquareCode, title: '机器人管理' },
      },
      {
        name: 'TelegramAccounts',
        path: 'telegram-accounts',
        component: () => import('#/views/telegram/accounts/index.vue'),
        meta: { icon: MonitorSmartphone, title: 'Telegram 账号' },
      },
      {
        name: 'TelegramBotButtons',
        path: 'telegram-buttons',
        component: () => import('#/views/telegram/buttons/index.vue'),
        meta: { icon: Grid, title: '按钮设置' },
      },
      {
        name: 'TronAddresses',
        path: 'tron-addresses',
        component: () => import('#/views/telegram/tron-addresses/index.vue'),
        meta: { icon: Settings2, title: 'TRON 地址监控' },
      },
      {
        name: 'TelegramBotSettings',
        path: 'settings',
        component: () => import('#/views/telegram/settings/index.vue'),
        meta: { icon: Settings2, title: '运行设置' },
      },
    ],
  },
];

export default routes;
