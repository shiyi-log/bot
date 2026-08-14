<script lang="ts" setup>
import type { DashboardRechargeItem } from '#/api/admin';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  Space,
  Table,
  Tag,
  Typography,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardRechargesApi } from '#/api/admin';

const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardRechargeItem[]>([]);
const router = useRouter();
const route = useRoute();

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 160,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 160,
  },
  { title: '币种', dataIndex: 'currency', key: 'currency', width: 100 },
  { title: '金额', dataIndex: 'amount', key: 'amount', width: 140 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '交易哈希', dataIndex: 'tx_hash', key: 'tx_hash', width: 320 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  {
    title: '完成时间',
    dataIndex: 'completed_at',
    key: 'completed_at',
    width: 170,
  },
  { title: '操作', key: 'actions', width: 100, fixed: 'right' as const },
];

function statusColor(status: string) {
  if (['completed'].includes(status)) return 'green';
  if (['pending'].includes(status)) return 'orange';
  if (['expired'].includes(status)) return 'red';
  return 'blue';
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: '已完成',
    expired: '已过期',
    pending: '待支付',
  };
  return labels[status] || status || '-';
}

function formatTime(value?: null | string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm') : value;
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardRechargesApi({
      keyword: keyword.value.trim(),
    });
  } finally {
    loading.value = false;
  }
}

function resetSearch() {
  keyword.value = '';
  loadData();
}

onMounted(() => {
  keyword.value =
    typeof route.query.keyword === 'string' ? route.query.keyword : '';
  loadData();
});

function goToDetail(rechargeId: number) {
  router.push(`/admin/cloud-orders/recharges/${rechargeId}`).catch(() => {});
}
</script>

<template>
  <Page description="读取 Django 充值订单数据" title="充值订单">
    <Card>
      <template #title>
        <Space>
          <span>充值数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索充值单号、币种、状态、交易哈希"
            style="width: 360px"
            @search="loadData"
          />
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        row-key="id"
        :scroll="{ x: 1740 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'id'">
            <a @click="goToDetail(Number(record.id))">{{ record.id }}</a>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="statusColor(record.status)">
              {{ record.status_label || statusLabel(record.status) }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'tx_hash'">
            <Typography.Paragraph
              :copyable="record.tx_hash ? { text: record.tx_hash } : false"
              class="!mb-0 break-all text-xs"
            >
              {{ record.tx_hash || '-' }}
            </Typography.Paragraph>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <span class="text-xs">{{ formatTime(record.created_at) }}</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a @click="goToDetail(Number(record.id))">详情</a>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
