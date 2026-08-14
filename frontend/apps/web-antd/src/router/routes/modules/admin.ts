import type { RouteRecordRaw } from 'vue-router';

import { MessageCircle, Settings2, Users } from '@vben/icons';

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
        name: 'TronAddresses',
        path: 'tron-addresses',
        component: () => import('#/views/telegram/tron-addresses/index.vue'),
        meta: { icon: Settings2, title: 'TRON 地址监控' },
      },
      {
        name: 'TelegramBotSettings',
        path: 'settings',
        component: () => import('#/views/telegram/settings/index.vue'),
        meta: { icon: Settings2, title: '机器人设置' },
      },
    ],
  },
];

export default routes;
