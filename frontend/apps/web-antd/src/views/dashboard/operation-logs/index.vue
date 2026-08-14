<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { DashboardBotOperationLogItem } from '#/api/admin';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Space, Table, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardBotOperationLogsApi } from '#/api/admin';

const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardBotOperationLogItem[]>([]);

const columns: TableColumnsType<DashboardBotOperationLogItem> = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', dataIndex: 'action_type', key: 'action_type', width: 110 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 150,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 160,
  },
  { title: 'TG ID', dataIndex: 'tg_user_id', key: 'tg_user_id', width: 140 },
  { title: '会话ID', dataIndex: 'chat_id', key: 'chat_id', width: 140 },
  { title: '消息ID', dataIndex: 'message_id', key: 'message_id', width: 120 },
  { title: '内容', dataIndex: 'payload', key: 'payload', width: 520 },
];

function actionColor(actionType: string) {
  if (actionType === 'callback') return 'processing';
  if (actionType === 'message') return 'success';
  return 'default';
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardBotOperationLogsApi({
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
  <Page
    description="记录用户在机器人里的消息和按钮点击，支持关键字搜索"
    title="操作日志"
  >
    <Card>
      <template #title>
        <Space>
          <span>机器人操作日志</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索用户 / 用户名 / TG ID / 按钮 / 消息内容"
            style="width: 400px"
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
        :scroll="{ x: 1600 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            <span>{{
              record.created_at
                ? dayjs(record.created_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'
            }}</span>
          </template>
          <template v-else-if="column.key === 'action_type'">
            <Tag :color="actionColor(record.action_type)">
              {{ record.action_label || record.action_type }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'payload'">
            <span class="whitespace-pre-wrap break-all">{{
              record.payload || '-'
            }}</span>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
