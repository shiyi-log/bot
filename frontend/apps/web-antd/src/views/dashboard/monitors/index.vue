<script lang="ts" setup>
import type { DashboardMonitorItem } from '#/api/admin';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';

import { getDashboardMonitorsApi } from '#/api/admin';

const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardMonitorItem[]>([]);

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '监控地址', dataIndex: 'address', key: 'address', width: 320 },
  { title: '用户', dataIndex: 'username', key: 'username', width: 180 },
  {
    title: 'Telegram ID',
    dataIndex: 'tg_user_id',
    key: 'tg_user_id',
    width: 160,
  },
  {
    title: '监控转账',
    dataIndex: 'monitor_transfers',
    key: 'monitor_transfers',
    width: 120,
  },
  {
    title: '监控资源',
    dataIndex: 'monitor_resources',
    key: 'monitor_resources',
    width: 120,
  },
  {
    title: '转账阈值',
    dataIndex: 'transfer_thresholds',
    key: 'transfer_thresholds',
    width: 180,
  },
  {
    title: '资源阈值',
    dataIndex: 'resource_thresholds',
    key: 'resource_thresholds',
    width: 180,
  },
  {
    title: '地址余额',
    dataIndex: 'chain_balance',
    key: 'chain_balance',
    width: 180,
  },
  {
    title: '今日收入',
    dataIndex: 'daily_income',
    key: 'daily_income',
    width: 140,
  },
  {
    title: '今日支出',
    dataIndex: 'daily_expense',
    key: 'daily_expense',
    width: 140,
  },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 100 },
  { title: '统计日期', dataIndex: 'stats_date', key: 'stats_date', width: 140 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 220 },
];

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardMonitorsApi({
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

onMounted(loadData);
</script>

<template>
  <Page description="查看地址监控与日统计数据" title="地址监控">
    <Card>
      <template #title>
        <Space>
          <span>地址监控数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索地址、备注、用户名、TG ID"
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
        :scroll="{ x: 2050 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'monitor_transfers'">
            <Tag :color="record.monitor_transfers ? 'blue' : 'default'">
              {{ record.monitor_transfers ? '开启' : '关闭' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'monitor_resources'">
            <Tag :color="record.monitor_resources ? 'purple' : 'default'">
              {{ record.monitor_resources ? '开启' : '关闭' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'transfer_thresholds'">
            USDT ≥ {{ record.usdt_threshold }} / TRX ≥
            {{ record.trx_threshold }}
          </template>
          <template v-else-if="column.key === 'resource_thresholds'">
            能量 ≥ {{ record.energy_threshold }} / 带宽 ≥
            {{ record.bandwidth_threshold }}
          </template>
          <template v-else-if="column.key === 'chain_balance'">
            <Space direction="vertical" :size="2">
              <Tag v-if="record.chain_balance_error" color="error">
查询失败
</Tag>
              <template v-else>
                <Tag color="green">
USDT {{ record.chain_usdt_balance ?? '0' }}
</Tag>
                <Tag color="purple">
TRX {{ record.chain_trx_balance ?? '0' }}
</Tag>
              </template>
            </Space>
          </template>
          <template v-else-if="column.key === 'daily_income'">
            {{ record.daily_income }} {{ record.daily_income_currency }}
          </template>
          <template v-else-if="column.key === 'daily_expense'">
            {{ record.daily_expense }} {{ record.daily_expense_currency }}
          </template>
          <template v-else-if="column.key === 'is_active'">
            <Tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '有效' : '停用' }}
            </Tag>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
