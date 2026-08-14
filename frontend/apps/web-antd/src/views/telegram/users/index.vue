<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type { TelegramUser } from '#/api/telegram';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getTelegramUsersApi } from '#/api/telegram';

const loading = ref(false);
const keyword = ref('');
const items = ref<TelegramUser[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });

const columns: TableColumnsType<TelegramUser> = [
  {
    title: 'Telegram 用户 ID',
    dataIndex: 'telegram_id',
    key: 'telegram_id',
    width: 190,
  },
  { title: '用户名', dataIndex: 'username', key: 'username', width: 180 },
  { title: '姓名', key: 'name', width: 180 },
  {
    title: '语言',
    dataIndex: 'language_code',
    key: 'language_code',
    width: 100,
  },
  {
    title: '消息数',
    dataIndex: 'message_count',
    key: 'message_count',
    width: 100,
  },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 120 },
  {
    title: '首次出现',
    dataIndex: 'first_seen_at',
    key: 'first_seen_at',
    width: 180,
  },
  {
    title: '最近活跃',
    dataIndex: 'last_seen_at',
    key: 'last_seen_at',
    width: 180,
  },
];

function formatDate(value: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

async function loadData() {
  loading.value = true;
  try {
    const result = await getTelegramUsersApi({
      search: keyword.value.trim(),
      page: pagination.page,
      page_size: pagination.pageSize,
    });
    items.value = result.results;
    pagination.total = result.count;
  } finally {
    loading.value = false;
  }
}

function search() {
  pagination.page = 1;
  loadData();
}

function resetSearch() {
  keyword.value = '';
  pagination.page = 1;
  loadData();
}

function handleTableChange(next: TablePaginationConfig) {
  pagination.page = next.current || 1;
  pagination.pageSize = next.pageSize || 20;
  loadData();
}

onMounted(loadData);
</script>

<template>
  <Page
    description="机器人收到消息后自动记录用户 ID 与基础资料"
    title="Telegram 用户"
  >
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>用户列表</span>
          <Space wrap>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索 ID、用户名或姓名"
              style="width: 320px"
              @search="search"
            />
            <Button @click="resetSearch">重置</Button>
            <Button @click="loadData">刷新</Button>
          </Space>
        </div>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }"
        row-key="id"
        :scroll="{ x: 1250 }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'name'">
            {{
              [record.first_name, record.last_name].filter(Boolean).join(' ') ||
              '-'
            }}
          </template>
          <template v-else-if="column.key === 'is_active'">
            <Tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '活跃' : '停用' }}
            </Tag>
            <Tag v-if="record.is_bot" color="blue">Bot</Tag>
          </template>
          <template
            v-else-if="
              column.key === 'first_seen_at' || column.key === 'last_seen_at'
            "
          >
            {{ formatDate(record[column.key]) }}
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
