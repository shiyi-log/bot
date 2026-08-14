import type { RouteRecordRaw } from 'vue-router';

import { User } from '@vben/icons';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'Profile',
    path: '/profile',
    component: () => import('#/views/_core/profile/index.vue'),
    meta: {
      icon: User,
      hideInMenu: true,
      title: $t('page.auth.profile'),
    },
  },
];

export default routes;
