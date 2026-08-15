<script lang="ts" setup>
import type { TelegramBot, TelegramBotPayload } from '#/api/telegram';
import type {
  FormInstance,
  TableColumnsType,
  TablePaginationConfig,
} from 'ant-design-vue';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Form,
  FormItem,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  createTelegramBotApi,
  deleteTelegramBotApi,
  getTelegramBotsApi,
  updateTelegramBotApi,
} from '#/api/telegram';

const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const editingId = ref<null | number>(null);
const keyword = ref('');
const enabledFilter = ref<'' | 'disabled' | 'enabled'>('');
const items = ref<TelegramBot[]>([]);
const formRef = ref<FormInstance>();
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
const form = reactive<TelegramBotPayload>({
  enabled: false,
  name: '',
  telegram_id: null,
  token_env_var: '',
  username: '',
  welcome_enabled: true,
  welcome_message: '欢迎 {first_name} 加入 {group_title}！',
});

const modalTitle = computed(() =>
  editingId.value ? '编辑机器人' : '新增机器人',
);
const columns: TableColumnsType<TelegramBot> = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '用户名', dataIndex: 'username', key: 'username', width: 170 },
  {
    title: 'Telegram ID',
    dataIndex: 'telegram_id',
    key: 'telegram_id',
    width: 180,
  },
  {
    title: '令牌环境变量',
    dataIndex: 'token_env_var',
    key: 'token_env_var',
    width: 210,
  },
  {
    title: '凭据',
    dataIndex: 'credential_configured',
    key: 'credential_configured',
    width: 110,
  },
  { title: '运行状态', dataIndex: 'enabled', key: 'enabled', width: 110 },
  {
    title: '欢迎消息',
    dataIndex: 'welcome_enabled',
    key: 'welcome_enabled',
    width: 110,
  },
  {
    title: '按钮数',
    dataIndex: 'button_count',
    key: 'button_count',
    width: 90,
  },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', fixed: 'right', width: 210 },
];

async function loadData() {
  loading.value = true;
  try {
    const result = await getTelegramBotsApi({
      enabled:
        enabledFilter.value === ''
          ? undefined
          : enabledFilter.value === 'enabled',
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

function openCreate() {
  editingId.value = null;
  Object.assign(form, {
    enabled: false,
    name: '',
    telegram_id: null,
    token_env_var: '',
    username: '',
    welcome_enabled: true,
    welcome_message: '欢迎 {first_name} 加入 {group_title}！',
  });
  formRef.value?.clearValidate();
  modalOpen.value = true;
}

function openEdit(record: Record<string, any>) {
  editingId.value = record.id;
  Object.assign(form, {
    enabled: record.enabled,
    name: record.name,
    telegram_id:
      record.telegram_id === null ? null : String(record.telegram_id),
    token_env_var: record.token_env_var,
    username: record.username,
    welcome_enabled: record.welcome_enabled,
    welcome_message: record.welcome_message,
  });
  formRef.value?.clearValidate();
  modalOpen.value = true;
}

async function saveBot() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    const telegramId = String(form.telegram_id ?? '').trim();
    const payload: TelegramBotPayload = {
      enabled: form.enabled,
      name: form.name.trim(),
      telegram_id: telegramId || null,
      token_env_var: form.token_env_var.trim(),
      username: form.username.trim().replace(/^@/, ''),
      welcome_enabled: form.welcome_enabled,
      welcome_message: form.welcome_message.trim(),
    };
    if (editingId.value) {
      await updateTelegramBotApi(editingId.value, payload);
    } else {
      await createTelegramBotApi(payload);
    }
    message.success(editingId.value ? '机器人已更新' : '机器人已创建');
    modalOpen.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function removeBot(id: number) {
  await deleteTelegramBotApi(id);
  message.success('机器人已删除');
  if (items.value.length === 1 && pagination.page > 1) pagination.page -= 1;
  await loadData();
}

function openButtons(bot: Record<string, any>) {
  router.push({
    path: '/admin/telegram-buttons',
    query: { bot: String(bot.id) },
  });
}

function search() {
  pagination.page = 1;
  loadData();
}

function resetFilters() {
  keyword.value = '';
  enabledFilter.value = '';
  pagination.page = 1;
  loadData();
}

function handleTableChange(next: TablePaginationConfig) {
  pagination.page = next.current || 1;
  pagination.pageSize = next.pageSize || 20;
  loadData();
}

function formatDate(value: string) {
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
}

onMounted(loadData);
</script>

<template>
  <Page
    description="每个机器人独立配置运行状态、令牌环境变量和欢迎消息"
    title="机器人管理"
  >
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>机器人列表</span>
          <Space wrap>
            <Select
              v-model:value="enabledFilter"
              allow-clear
              placeholder="运行状态"
              style="width: 130px"
              @change="search"
            >
              <Select.Option value="enabled">已启用</Select.Option>
              <Select.Option value="disabled">已停用</Select.Option>
            </Select>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索名称、用户名或环境变量"
              style="width: 320px"
              @search="search"
            />
            <Button @click="resetFilters">重置</Button>
            <Button @click="loadData">刷新</Button>
            <Button type="primary" @click="openCreate">新增机器人</Button>
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
        :scroll="{ x: 1570 }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'telegram_id'">
            {{ record.telegram_id ?? '-' }}
          </template>
          <template v-else-if="column.key === 'credential_configured'">
            <Tag :color="record.credential_configured ? 'success' : 'warning'">
              {{ record.credential_configured ? '已配置' : '未配置' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'enabled'">
            <Tag :color="record.enabled ? 'success' : 'default'">
              {{ record.enabled ? '已启用' : '已停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'welcome_enabled'">
            <Tag :color="record.welcome_enabled ? 'processing' : 'default'">
              {{ record.welcome_enabled ? '发送' : '关闭' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'button_count'">
            <Button size="small" type="link" @click="openButtons(record)">
              {{ record.button_count }}
            </Button>
          </template>
          <template v-else-if="column.key === 'updated_at'">
            {{ formatDate(record.updated_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button size="small" type="link" @click="openEdit(record)"
                >编辑</Button
              >
              <Button size="small" type="link" @click="openButtons(record)"
                >按钮</Button
              >
              <Popconfirm
                title="删除机器人会同时删除它的按钮配置，确认继续？"
                @confirm="removeBot(record.id)"
              >
                <Button danger size="small" type="link">删除</Button>
              </Popconfirm>
            </Space>
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="modalOpen"
      :confirm-loading="saving"
      :title="modalTitle"
      ok-text="保存"
      width="680px"
      @ok="saveBot"
    >
      <Form ref="formRef" :model="form" layout="vertical">
        <FormItem
          label="名称"
          name="name"
          :rules="[{ required: true, message: '请输入机器人名称' }]"
        >
          <Input
            v-model:value="form.name"
            :maxlength="128"
            placeholder="例如：主服务机器人"
          />
        </FormItem>
        <FormItem label="用户名" name="username">
          <Input
            v-model:value="form.username"
            :maxlength="64"
            placeholder="不含或包含 @ 均可"
          />
        </FormItem>
        <FormItem label="Telegram ID" name="telegram_id">
          <Input
            :value="form.telegram_id ?? ''"
            placeholder="可选，使用文本输入避免 64 位精度丢失"
            @update:value="form.telegram_id = $event || null"
          />
        </FormItem>
        <FormItem
          label="令牌环境变量"
          name="token_env_var"
          :rules="[
            { required: true, message: '请输入令牌环境变量名' },
            {
              pattern: /^[A-Z][A-Z0-9_]{2,63}$/,
              message: '请输入大写环境变量名，例如 BOT_MAIN_TOKEN',
            },
          ]"
        >
          <Input
            v-model:value="form.token_env_var"
            :maxlength="64"
            placeholder="BOT_MAIN_TOKEN"
          />
        </FormItem>
        <Alert
          class="mb-4"
          message="这里只保存环境变量名。机器人令牌必须在服务端环境中配置。"
          show-icon
          type="info"
        />
        <FormItem label="启用机器人">
          <Switch v-model:checked="form.enabled" />
        </FormItem>
        <FormItem label="发送欢迎消息">
          <Switch v-model:checked="form.welcome_enabled" />
        </FormItem>
        <FormItem
          label="欢迎消息"
          name="welcome_message"
          :rules="[{ required: true, message: '请输入欢迎消息' }]"
        >
          <Input.TextArea
            v-model:value="form.welcome_message"
            :auto-size="{ minRows: 4, maxRows: 10 }"
            :disabled="!form.welcome_enabled"
            :maxlength="2000"
            placeholder="欢迎 {first_name} 加入 {group_title}！"
            show-count
          />
        </FormItem>
        <Alert
          message="可用变量：{first_name}、{last_name}、{username}、{user_id}、{group_title}、{group_id}"
          show-icon
          type="info"
        />
      </Form>
    </Modal>
  </Page>
</template>
