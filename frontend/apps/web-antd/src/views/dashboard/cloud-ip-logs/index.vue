<script lang="ts" setup>
import dayjs from 'dayjs';
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import type { TableColumnsType } from 'ant-design-vue';

import { getDashboardCloudIpLogsApi, type DashboardCloudIpLogItem } from '#/api/admin';

const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardCloudIpLogItem[]>([]);

const columns: TableColumnsType<DashboardCloudIpLogItem> = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '事件', dataIndex: 'event_type', key: 'event_type', width: 100 },
  { title: '用户', dataIndex: 'user_display_name', key: 'user_display_name', width: 140 },
  { title: '用户名', dataIndex: 'username_label', key: 'username_label', width: 160 },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 180 },
  { title: '资产名称', dataIndex: 'asset_name', key: 'asset_name', width: 180 },
  { title: '厂商', dataIndex: 'provider_label', key: 'provider_label', width: 120 },
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 140 },
  { title: '旧IP', dataIndex: 'previous_public_ip', key: 'previous_public_ip', width: 140 },
  { title: '当前IP', dataIndex: 'public_ip', key: 'public_ip', width: 140 },
  { title: '实例ID', dataIndex: 'instance_id', key: 'instance_id', width: 180 },
  { title: '说明', dataIndex: 'note', key: 'note', width: 280 },
];

function eventColor(eventType: string) {
  if (eventType === 'created') return 'success';
  if (eventType === 'changed') return 'processing';
  if (eventType === 'expired' || eventType === 'suspended') return 'warning';
  if (eventType === 'deleted' || eventType === 'recycled') return 'error';
  return 'default';
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardCloudIpLogsApi({ keyword: keyword.value.trim() });
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
  <Page description="记录云服务器 IP 从创建、变更、到期、延停到删除/回收的全过程，支持关键字搜索" title="IP日志">
    <Card>
      <template #title>
        <Space>
          <span>IP 变化日志</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索订单号 / 用户 / IP / 实例ID / 说明"
            style="width: 360px"
            @search="loadData"
          />
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>
      <Table :columns="columns" :data-source="items" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1800 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            <span>{{ record.created_at ? dayjs(record.created_at).format('YYYY-MM-DD HH:mm:ss') : '-' }}</span>
          </template>
          <template v-else-if="column.key === 'event_type'">
            <Tag :color="eventColor(record.event_type)">{{ record.event_label || record.event_type }}</Tag>
          </template>
          <template v-else-if="column.key === 'note'">
            <span>{{ record.note || '-' }}</span>
          </template>
          <template v-else-if="['previous_public_ip', 'public_ip'].includes(String(column.key))">
            <Tag>{{ (record as any)[String(column.key)] || '-' }}</Tag>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
