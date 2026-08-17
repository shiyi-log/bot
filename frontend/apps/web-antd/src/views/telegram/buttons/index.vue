<script lang="ts" setup>
import type {
  TelegramBot,
  TelegramBotButton,
  TelegramBotButtonPayload,
} from '#/api/telegram';
import type {
  FormInstance,
  TableColumnsType,
  TablePaginationConfig,
} from 'ant-design-vue';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Form,
  FormItem,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'ant-design-vue';

import {
  createTelegramBotButtonApi,
  deleteTelegramBotButtonApi,
  getTelegramBotButtonsApi,
  getTelegramBotsApi,
  updateTelegramBotButtonApi,
} from '#/api/telegram';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const botLoading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const editingId = ref<null | number>(null);
const selectedBot = ref<number>();
const keyword = ref('');
const bots = ref<TelegramBot[]>([]);
const items = ref<TelegramBotButton[]>([]);
const formRef = ref<FormInstance>();
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
const form = reactive<TelegramBotButtonPayload>({
  bot: 0,
  enabled: true,
  position: 1,
  row: 1,
  text: '',
  url: '',
});

const modalTitle = computed(() => (editingId.value ? '编辑按钮' : '新增按钮'));
const columns: TableColumnsType<TelegramBotButton> = [
  {
    title: '机器人',
    dataIndex: 'bot_name',
    key: 'bot_name',
    fixed: 'left',
    width: 180,
  },
  { title: '按钮文字', dataIndex: 'text', key: 'text', width: 180 },
  { title: '链接', dataIndex: 'url', key: 'url', width: 360 },
  { title: '行', dataIndex: 'row', key: 'row', width: 80 },
  { title: '列', dataIndex: 'position', key: 'position', width: 80 },
  { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', fixed: 'right', width: 150 },
];

async function loadBots() {
  botLoading.value = true;
  try {
    const result = await getTelegramBotsApi({ page: 1, page_size: 100 });
    bots.value = result.results;
    const requestedId = Number(route.query.bot);
    const requestedBot = bots.value.find((bot) => bot.id === requestedId);
    selectedBot.value = requestedBot?.id ?? bots.value[0]?.id;
  } finally {
    botLoading.value = false;
  }
}

async function loadData() {
  if (!selectedBot.value) {
    items.value = [];
    pagination.total = 0;
    return;
  }
  loading.value = true;
  try {
    const result = await getTelegramBotButtonsApi({
      bot: selectedBot.value,
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

function changeBot() {
  pagination.page = 1;
  if (selectedBot.value) {
    router.replace({
      path: route.path,
      query: { bot: String(selectedBot.value) },
    });
  }
  loadData();
}

function openCreate() {
  if (!selectedBot.value) return;
  editingId.value = null;
  Object.assign(form, {
    bot: selectedBot.value,
    enabled: true,
    position: 1,
    row: 1,
    text: '',
    url: '',
  });
  formRef.value?.clearValidate();
  modalOpen.value = true;
}

function openEdit(record: Record<string, any>) {
  editingId.value = record.id;
  Object.assign(form, {
    bot: record.bot,
    enabled: record.enabled,
    position: record.position,
    row: record.row,
    text: record.text,
    url: record.url,
  });
  formRef.value?.clearValidate();
  modalOpen.value = true;
}

async function saveButton() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    const payload: TelegramBotButtonPayload = {
      bot: form.bot,
      enabled: form.enabled,
      position: form.position,
      row: form.row,
      text: form.text.trim(),
      url: form.url.trim(),
    };
    if (editingId.value) {
      await updateTelegramBotButtonApi(editingId.value, payload);
    } else {
      await createTelegramBotButtonApi(payload);
    }
    message.success(editingId.value ? '按钮已更新' : '按钮已创建');
    modalOpen.value = false;
    selectedBot.value = payload.bot;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function removeButton(id: number) {
  await deleteTelegramBotButtonApi(id);
  message.success('按钮已删除');
  if (items.value.length === 1 && pagination.page > 1) pagination.page -= 1;
  await loadData();
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

onMounted(async () => {
  await loadBots();
  await loadData();
});
</script>

<template>
  <Page
    description="配置机器人在开始和欢迎消息中发送的链接按钮"
    title="按钮设置"
  >
    <Alert
      class="mb-4"
      message="启用的按钮会按行号和列号组成 Telegram 内联键盘，并随 /start、首次私聊欢迎和新成员欢迎消息发送。"
      show-icon
      type="info"
    />
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>按钮列表</span>
          <Space wrap>
            <Select
              v-model:value="selectedBot"
              :loading="botLoading"
              placeholder="选择机器人"
              style="width: 240px"
              @change="changeBot"
            >
              <Select.Option v-for="bot in bots" :key="bot.id" :value="bot.id">
                {{ bot.name }}
              </Select.Option>
            </Select>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索按钮文字或链接"
              style="width: 300px"
              @search="search"
            />
            <Button @click="resetSearch">重置</Button>
            <Button @click="loadData">刷新</Button>
            <Button :disabled="!selectedBot" type="primary" @click="openCreate">
              新增按钮
            </Button>
          </Space>
        </div>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :locale="{ emptyText: bots.length ? '暂无按钮' : '请先创建机器人' }"
        :pagination="{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }"
        row-key="id"
        :scroll="{ x: 1130 }"
        sticky
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'bot_name'">
            <Tag color="blue">{{ record.bot_name }}</Tag>
          </template>
          <template v-else-if="column.key === 'url'">
            <a :href="record.url" rel="noopener noreferrer" target="_blank">
              {{ record.url }}
            </a>
          </template>
          <template v-else-if="column.key === 'enabled'">
            <Tag :color="record.enabled ? 'success' : 'default'">
              {{ record.enabled ? '已启用' : '已停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button size="small" type="link" @click="openEdit(record)"
                >编辑</Button
              >
              <Popconfirm
                title="确认删除这个按钮？"
                @confirm="removeButton(record.id)"
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
      width="600px"
      @ok="saveButton"
    >
      <Form ref="formRef" :model="form" layout="vertical">
        <FormItem
          label="机器人"
          name="bot"
          :rules="[{ required: true, message: '请选择机器人' }]"
        >
          <Select v-model:value="form.bot">
            <Select.Option v-for="bot in bots" :key="bot.id" :value="bot.id">
              {{ bot.name }}
            </Select.Option>
          </Select>
        </FormItem>
        <FormItem
          label="按钮文字"
          name="text"
          :rules="[{ required: true, message: '请输入按钮文字' }]"
        >
          <Input
            v-model:value="form.text"
            :maxlength="64"
            placeholder="例如：打开帮助中心"
            show-count
          />
        </FormItem>
        <FormItem
          label="链接"
          name="url"
          :rules="[
            { required: true, message: '请输入链接' },
            { type: 'url', message: '请输入完整的 http 或 https 链接' },
          ]"
        >
          <Input
            v-model:value="form.url"
            :maxlength="500"
            placeholder="https://example.com"
          />
        </FormItem>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormItem
            label="行号"
            name="row"
            :rules="[{ required: true, message: '请输入行号' }]"
          >
            <InputNumber
              v-model:value="form.row"
              :max="20"
              :min="1"
              class="w-full"
            />
          </FormItem>
          <FormItem
            label="列号"
            name="position"
            :rules="[{ required: true, message: '请输入列号' }]"
          >
            <InputNumber
              v-model:value="form.position"
              :max="8"
              :min="1"
              class="w-full"
            />
          </FormItem>
        </div>
        <FormItem label="启用按钮">
          <Switch v-model:checked="form.enabled" />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>
