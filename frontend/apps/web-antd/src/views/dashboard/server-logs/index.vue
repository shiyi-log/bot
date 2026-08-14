<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { DashboardCloudIpLogItem } from '#/api/admin';

import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardCloudIpLogsApi } from '#/api/admin';

const router = useRouter();
const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardCloudIpLogItem[]>([]);
const expandedNotes = ref<Record<string, boolean>>({});

const columns: TableColumnsType<DashboardCloudIpLogItem> = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '事件', dataIndex: 'event_type', key: 'event_type', width: 100 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 140,
  },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 180 },
  { title: '服务器', dataIndex: 'asset_name', key: 'asset_name', width: 180 },
  { title: '当前IP', dataIndex: 'public_ip', key: 'public_ip', width: 140 },
  { title: '实例ID', dataIndex: 'instance_id', key: 'instance_id', width: 180 },
  { title: '说明', dataIndex: 'note', key: 'note', width: 520 },
  { title: '详情', dataIndex: 'detail_path', key: 'detail_path', width: 100 },
];

function eventColor(eventType: string) {
  if (eventType === 'created') return 'success';
  if (eventType === 'deleted') return 'error';
  if (eventType === 'changed') return 'processing';
  return 'default';
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardCloudIpLogsApi({
      keyword: keyword.value.trim(),
      log_type: 'server',
    });
  } finally {
    loading.value = false;
  }
}

function resetSearch() {
  keyword.value = '';
  loadData();
}

function openDetail(path?: string) {
  if (!path) return;
  router.push(path).catch(() => {});
}

function noteKey(record: Record<string, any>) {
  return String(
    record.id ||
      record.order_no ||
      record.asset_name ||
      record.created_at ||
      'note',
  );
}

function noteTooLong(text?: null | string) {
  const value = String(text || '').trim();
  if (!value) return false;
  return value.length > 120 || value.split('\n').filter(Boolean).length > 2;
}

function toggleNote(record: Record<string, any>) {
  const key = noteKey(record);
  expandedNotes.value[key] = !expandedNotes.value[key];
}

function noteExpanded(record: Record<string, any>) {
  return Boolean(expandedNotes.value[noteKey(record)]);
}

onMounted(loadData);
</script>

<template>
  <Page
    description="服务器生命周期主链总览，集中查看创建、分配IP、关机、删机与回收等关键过程"
    title="服务器日志"
  >
    <Card>
      <template #title>
        <Space>
          <span>服务器日志 / 主链总览</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索订单号 / 用户 / 服务器 / IP / 说明"
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
        row-key="id"
        :pagination="{ pageSize: 20 }"
        :scroll="{ x: 1700 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            <span>{{
              record.created_at
                ? dayjs(record.created_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'
            }}</span>
          </template>
          <template v-else-if="column.key === 'event_type'">
            <Tag :color="eventColor(record.event_type)">
              {{ record.event_label || record.event_type }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'order_no'">
            <Button
              v-if="record.order_detail_path"
              size="small"
              type="link"
              @click="openDetail(record.order_detail_path)"
            >
              {{ record.order_no || '-' }}
            </Button>
            <span v-else>{{ record.order_no || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'asset_name'">
            <Button
              v-if="record.asset_detail_path"
              size="small"
              type="link"
              @click="openDetail(record.asset_detail_path)"
            >
              {{ record.asset_name || '-' }}
            </Button>
            <span v-else>{{ record.asset_name || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'note'">
            <div class="flex flex-col gap-2">
              <span
                class="whitespace-pre-wrap break-all"
                :class="[
                  !noteExpanded(record) && noteTooLong(record.note)
                    ? 'collapsed-note'
                    : '',
                ]"
              >
                {{ record.note || '-' }}
              </span>
              <Button
                v-if="noteTooLong(record.note)"
                size="small"
                type="link"
                @click="toggleNote(record)"
              >
                {{ noteExpanded(record) ? '收起' : '展开' }}
              </Button>
            </div>
          </template>
          <template v-else-if="column.key === 'detail_path'">
            <Button
              v-if="record.detail_path"
              size="small"
              type="link"
              @click="openDetail(record.detail_path)"
            >
              详情
            </Button>
            <span v-else>-</span>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>

<style scoped>
.collapsed-note {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
</style>
