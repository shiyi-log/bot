<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  TelegramBot,
  TelegramGroup,
  TelegramGroupMember,
} from '#/api/telegram';

import { onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Select, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getTelegramBotsApi,
  getTelegramGroupMembersApi,
  getTelegramGroupsApi,
} from '#/api/telegram';

const route = useRoute();
const loading = ref(false);
const groupLoading = ref(false);
const botLoading = ref(false);
const keyword = ref('');
const selectedBot = ref<number>();
const selectedGroup = ref<number>();
const bots = ref<TelegramBot[]>([]);
const groups = ref<TelegramGroup[]>([]);
const items = ref<TelegramGroupMember[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });

const columns: TableColumnsType<TelegramGroupMember> = [
  {
    title: '机器人',
    dataIndex: 'bot_name',
    key: 'bot_name',
    fixed: 'left',
    width: 180,
  },
  { title: '群组', dataIndex: 'group_title', key: 'group_title', width: 220 },
  {
    title: '群组 ID',
    dataIndex: 'group_telegram_id',
    key: 'group_telegram_id',
    width: 190,
  },
  {
    title: '用户 ID',
    dataIndex: 'telegram_user_id',
    key: 'telegram_user_id',
    width: 180,
  },
  { title: '用户名', dataIndex: 'username', key: 'username', width: 180 },
  { title: '姓名', key: 'name', width: 180 },
  {
    title: '发言数',
    dataIndex: 'message_count',
    key: 'message_count',
    width: 100,
  },
  {
    title: '首次发言',
    dataIndex: 'first_spoke_at',
    key: 'first_spoke_at',
    width: 180,
  },
  {
    title: '最后发言',
    dataIndex: 'last_spoke_at',
    key: 'last_spoke_at',
    width: 180,
  },
];

function formatDate(value: string) {
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
}

async function loadGroups() {
  groupLoading.value = true;
  try {
    const result = await getTelegramGroupsApi({ page: 1, page_size: 100 });
    groups.value = result.results.filter(
      (group) => group.group_type !== 'channel',
    );
  } finally {
    groupLoading.value = false;
  }
}

async function loadBots() {
  botLoading.value = true;
  try {
    const result = await getTelegramBotsApi({ page: 1, page_size: 100 });
    bots.value = result.results;
  } finally {
    botLoading.value = false;
  }
}

async function loadData() {
  loading.value = true;
  try {
    const result = await getTelegramGroupMembersApi({
      bot: selectedBot.value,
      group: selectedGroup.value,
      page: pagination.page,
      page_size: pagination.pageSize,
      search: keyword.value.trim(),
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

function resetFilters() {
  keyword.value = '';
  selectedBot.value = undefined;
  selectedGroup.value = undefined;
  pagination.page = 1;
  loadData();
}

function handleTableChange(next: TablePaginationConfig) {
  pagination.page = next.current || 1;
  pagination.pageSize = next.pageSize || 20;
  loadData();
}

onMounted(async () => {
  const groupId = Number(route.query.group);
  const botId = Number(route.query.bot);
  selectedGroup.value =
    Number.isInteger(groupId) && groupId > 0 ? groupId : undefined;
  selectedBot.value = Number.isInteger(botId) && botId > 0 ? botId : undefined;
  await Promise.all([loadBots(), loadGroups(), loadData()]);
});
</script>

<template>
  <Page
    description="成员仅在群组或超级群组中发言后进入列表，资料随下一次发言更新"
    title="群组成员"
  >
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>发言成员</span>
          <Space wrap>
            <Select
              v-model:value="selectedBot"
              allow-clear
              :loading="botLoading"
              placeholder="筛选机器人"
              style="width: 220px"
              @change="search"
            >
              <Select.Option v-for="bot in bots" :key="bot.id" :value="bot.id">
                {{ bot.name }}
              </Select.Option>
            </Select>
            <Select
              v-model:value="selectedGroup"
              allow-clear
              :loading="groupLoading"
              placeholder="筛选群组"
              style="width: 240px"
              @change="search"
            >
              <Select.Option
                v-for="group in groups"
                :key="group.id"
                :value="group.id"
              >
                {{ group.title || group.telegram_id }}
              </Select.Option>
            </Select>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索群组、用户 ID、用户名或姓名"
              style="width: 320px"
              @search="search"
            />
            <Button @click="resetFilters">重置</Button>
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
        :scroll="{ x: 1350 }"
        sticky
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'bot_name'">
            <Tag color="purple">{{ record.bot_name }}</Tag>
          </template>
          <template v-else-if="column.key === 'group_title'">
            <Tag color="blue">{{
              record.group_title || record.group_telegram_id
            }}</Tag>
          </template>
          <template v-else-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'name'">
            {{
              [record.first_name, record.last_name].filter(Boolean).join(' ') ||
              '-'
            }}
          </template>
          <template
            v-else-if="
              column.key === 'first_spoke_at' || column.key === 'last_spoke_at'
            "
          >
            {{ formatDate(record[column.key]) }}
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
