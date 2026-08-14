<script lang="ts" setup>
import dayjs from 'dayjs';
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Empty, Space, Table, Tag, Typography, message } from 'ant-design-vue';

import {
  getDashboardUserBalanceDetailsApi,
  type DashboardUserBalanceDetailItem,
  type DashboardUserItem,
} from '#/api/admin';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const user = ref<DashboardUserItem | null>(null);
const items = ref<DashboardUserBalanceDetailItem[]>([]);

const userId = computed(() => Number(route.params.id || 0));

const columns = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '类型', dataIndex: 'type_label', key: 'type_label', width: 140 },
  { title: '方向', dataIndex: 'direction', key: 'direction', width: 100 },
  { title: '币种', dataIndex: 'currency', key: 'currency', width: 100 },
  { title: '变动金额', dataIndex: 'amount', key: 'amount', width: 140 },
  { title: '变动前余额', dataIndex: 'before_balance', key: 'before_balance', width: 150 },
  { title: '变动后余额', dataIndex: 'after_balance', key: 'after_balance', width: 150 },
  { title: '说明', dataIndex: 'description', key: 'description' },
  { title: '操作', key: 'actions', width: 100, fixed: 'right' as const },
];

function formatTime(value?: null | string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}

function directionColor(direction: string) {
  return direction === 'in' ? 'green' : 'red';
}

function amountText(record: DashboardUserBalanceDetailItem) {
  const prefix = record.direction === 'in' ? '+' : '-';
  return `${prefix}${record.amount}`;
}

async function loadData() {
  if (!userId.value) {
    message.error('用户 ID 不正确');
    return;
  }
  loading.value = true;
  try {
    const result = await getDashboardUserBalanceDetailsApi(userId.value);
    user.value = result.user;
    items.value = result.items;
  } catch {
    user.value = null;
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push('/admin/users').catch(() => {});
}

function openRelated(record: DashboardUserBalanceDetailItem) {
  if (!record.related_path) return;
  router.push(record.related_path).catch(() => {});
}

onMounted(loadData);
</script>

<template>
  <Page description="查看用户余额收入与支出明细" title="余额明细">
    <Card :loading="loading">
      <template #title>
        <Space>
          <Button size="small" @click="goBack">返回用户列表</Button>
          <span>余额明细</span>
          <span v-if="user">{{ user.display_name || '-' }} / TG {{ user.tg_user_id }}</span>
          <Tag v-if="user" color="blue">USDT {{ user.balance }}</Tag>
          <Tag v-if="user" color="purple">TRX {{ user.balance_trx }}</Tag>
        </Space>
      </template>

      <Table
        v-if="items.length"
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        row-key="id"
        :scroll="{ x: 1500 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            <span class="text-xs">{{ formatTime((record as DashboardUserBalanceDetailItem).created_at) }}</span>
          </template>
          <template v-else-if="column.key === 'direction'">
            <Tag :color="directionColor((record as DashboardUserBalanceDetailItem).direction)">
              {{ (record as DashboardUserBalanceDetailItem).direction_label }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'before_balance'">
            <span>{{ (record as DashboardUserBalanceDetailItem).before_balance || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'after_balance'">
            <span>{{ (record as DashboardUserBalanceDetailItem).after_balance || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'amount'">
            <Typography.Text :type="(record as DashboardUserBalanceDetailItem).direction === 'in' ? 'success' : 'danger'">
              {{ amountText(record as DashboardUserBalanceDetailItem) }}
            </Typography.Text>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a
              v-if="(record as DashboardUserBalanceDetailItem).related_path"
              @click="openRelated(record as DashboardUserBalanceDetailItem)"
            >
              详情
            </a>
            <span v-else class="text-gray-400">-</span>
          </template>
        </template>
      </Table>

      <Empty v-else-if="!loading" description="暂无余额明细" />
    </Card>
  </Page>
</template>
