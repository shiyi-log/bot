<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type { TelegramGroup } from '#/api/telegram';

import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getTelegramGroupsApi } from '#/api/telegram';

const loading = ref(false);
const router = useRouter();
const keyword = ref('');
const items = ref<TelegramGroup[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });

const columns: TableColumnsType<TelegramGroup> = [
  {
    title: 'Telegram 群组 ID',
    dataIndex: 'telegram_id',
    key: 'telegram_id',
    fixed: 'left',
    width: 200,
  },
  { title: '群组名称', dataIndex: 'title', key: 'title', width: 240 },
  { title: '公开用户名', dataIndex: 'username', key: 'username', width: 180 },
  { title: '类型', dataIndex: 'group_type', key: 'group_type', width: 120 },
  {
    title: '消息数',
    dataIndex: 'message_count',
    key: 'message_count',
    width: 100,
  },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 100 },
  {
    title: '成员数',
    dataIndex: 'member_count',
    key: 'member_count',
    width: 100,
  },
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
  { title: '操作', key: 'action', fixed: 'right', width: 110 },
];

const groupTypeLabels: Record<string, string> = {
  channel: '频道',
  group: '群组',
  supergroup: '超级群组',
};

function formatDate(value: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

async function loadData() {
  loading.value = true;
  try {
    const result = await getTelegramGroupsApi({
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

function viewMembers(record: Record<string, any>) {
  router.push({
    path: '/admin/telegram-group-members',
    query: { group: String(record.id) },
  });
}

onMounted(loadData);
</script>

<template>
  <Page
    description="机器人加入群组后自动记录群组 ID 与基础资料"
    title="Telegram 群组"
  >
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>群组列表</span>
          <Space wrap>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索群组 ID、名称或用户名"
              style="width: 340px"
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
        :scroll="{ x: 1450 }"
        sticky
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'group_type'">
            <Tag color="blue">{{
              groupTypeLabels[record.group_type] || record.group_type
            }}</Tag>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <Tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '活跃' : '停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <Button size="small" type="link" @click="viewMembers(record)">
              查看成员
            </Button>
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
