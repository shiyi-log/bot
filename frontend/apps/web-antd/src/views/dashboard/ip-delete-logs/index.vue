<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { DashboardUnattachedIpDeletePlan } from '#/api/admin';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardIpDeleteLogsApi } from '#/api/admin';

const router = useRouter();
const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardUnattachedIpDeletePlan[]>([]);
const expandedNotes = ref<Record<string, boolean>>({});

const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  if (!text) return items.value;
  return items.value.filter((item) =>
    [
      item.public_ip,
      item.asset_name,
      item.provider_status,
      item.user_display_name,
      item.username_label,
      item.display_note,
      item.note,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(text)),
  );
});

const columns: TableColumnsType<DashboardUnattachedIpDeletePlan> = [
  { title: 'IP', dataIndex: 'public_ip', key: 'public_ip', width: 150 },
  {
    title: '固定IP名/资产名',
    dataIndex: 'asset_name',
    key: 'asset_name',
    width: 220,
  },
  {
    title: '状态',
    dataIndex: 'provider_status',
    key: 'provider_status',
    width: 160,
  },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 170,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 170,
  },
  {
    title: '服务到期/发现时间',
    dataIndex: 'actual_expires_at',
    key: 'actual_expires_at',
    width: 190,
  },
  { title: 'IP删除时间', dataIndex: 'delete_at', key: 'delete_at', width: 190 },
  { title: '日志时间', dataIndex: 'logged_at', key: 'logged_at', width: 190 },
  { title: '说明', dataIndex: 'note', key: 'note', width: 520 },
  { title: '操作', key: 'actions', fixed: 'right', width: 110 },
];

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function deleteColor(record: Record<string, any>) {
  if (record.is_overdue) return 'red';
  if (!record.delete_at) return 'default';
  const hours = dayjs(record.delete_at).diff(dayjs(), 'hour');
  if (hours <= 24) return 'volcano';
  if (hours <= 72) return 'orange';
  if (hours <= 7 * 24) return 'gold';
  return 'blue';
}

function statusColor(record: Record<string, any>) {
  if (record.is_overdue) return 'red';
  if ((record.provider_status || '').includes('未附加')) return 'warning';
  return 'processing';
}

function openDetail(path?: string) {
  if (!path) return;
  router.push(path).catch(() => {});
}

function noteKey(record: Record<string, any>) {
  return String(record.id || record.asset_name || record.public_ip || 'note');
}

function displayNote(record: Record<string, any>) {
  return record.display_note || record.note || '-';
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

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardIpDeleteLogsApi({ limit: 300 });
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
  <Page
    description="只看固定 IP 恢复与回收链路，集中核对固定IP名、用户、计划时间与最终执行结果。"
    title="固定IP恢复表"
  >
    <Card :loading="loading">
      <template #title>
        <Space wrap>
          <span>固定IP恢复 / 回收日志</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索 IP / 资产名 / 用户 / 备注"
            style="width: 360px"
            @search="loadData"
          />
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
          <Tag color="blue">共 {{ filteredItems.length }} 条</Tag>
        </Space>
      </template>
      <Table
        :columns="columns"
        :data-source="filteredItems"
        :pagination="{ pageSize: 20 }"
        row-key="id"
        :scroll="{ x: 1810 }"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'public_ip'">
            <Tag>{{ record.public_ip || '-' }}</Tag>
          </template>
          <template v-else-if="column.key === 'provider_status'">
            <Tag :color="statusColor(record)">
              {{ record.provider_status || '未附加IP' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'actual_expires_at'">
            {{ formatTime(record.actual_expires_at) }}
          </template>
          <template v-else-if="column.key === 'delete_at'">
            <Tag :color="deleteColor(record)">
              {{ formatTime(record.delete_at) }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'logged_at'">
            {{ formatTime(record.logged_at) }}
          </template>
          <template v-else-if="column.key === 'note'">
            <div class="flex flex-col gap-2">
              <span
                class="whitespace-pre-wrap break-all"
                :class="[
                  !noteExpanded(record) && noteTooLong(displayNote(record))
                    ? 'collapsed-note'
                    : '',
                ]"
              >
                {{ displayNote(record) }}
              </span>
              <Button
                v-if="noteTooLong(displayNote(record))"
                size="small"
                type="link"
                @click="toggleNote(record)"
              >
                {{ noteExpanded(record) ? '收起' : '展开' }}
              </Button>
            </div>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Button
              v-if="record.asset_detail_path || record.detail_path"
              type="link"
              size="small"
              @click="
                openDetail(record.asset_detail_path || record.detail_path)
              "
            >
              资产详情
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
