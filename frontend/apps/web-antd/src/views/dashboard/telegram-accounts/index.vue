<script lang="ts" setup>
import type {
  DashboardTelegramAccountsOverview,
  DashboardTelegramChatUserItem,
  DashboardTelegramLoginAccountCreatePayload,
  DashboardTelegramMessageItem,
} from '#/api/admin';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  List,
  message,
  Modal,
  Row,
  Space,
  Tag,
} from 'ant-design-vue';

import {
  createDashboardTelegramAccountApi,
  getDashboardTelegramAccountsApi,
  getDashboardTelegramMessagesApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const open = ref(false);
const keyword = ref('');
const selectedUser = ref<DashboardTelegramChatUserItem | null>(null);
const messages = ref<DashboardTelegramMessageItem[]>([]);
const overview = ref<DashboardTelegramAccountsOverview>({
  accounts: [],
  chats: [],
  messages: [],
  users: [],
});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const form = reactive<DashboardTelegramLoginAccountCreatePayload>({
  label: '',
  note: '',
  phone: '',
  tg_user_id: '',
  username: '',
});

async function loadData() {
  loading.value = true;
  try {
    overview.value = await getDashboardTelegramAccountsApi({
      keyword: keyword.value || undefined,
      scope: 'users',
    });
  } finally {
    loading.value = false;
  }
}

async function selectUser(user: DashboardTelegramChatUserItem) {
  selectedUser.value = user;
  messages.value = await getDashboardTelegramMessagesApi({
    tg_user_id: user.tg_user_id,
  });
}

function openCreate() {
  if (!requireCloudDangerPermission('添加 Telegram 登录账号')) return;
  form.label = '';
  form.phone = '';
  form.tg_user_id = '';
  form.username = '';
  form.note = '';
  open.value = true;
}

async function saveAccount() {
  if (!requireCloudDangerPermission('保存 Telegram 登录账号')) return;
  saving.value = true;
  try {
    await createDashboardTelegramAccountApi(form);
    message.success('账号已登记');
    open.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

function usernameText(user: DashboardTelegramChatUserItem) {
  return user.primary_username
    ? `@${user.primary_username}`
    : `ID ${user.tg_user_id}`;
}

onMounted(loadData);
</script>

<template>
  <Page
    title="账号管理"
    description="管理 Telegram 账号登记、bot 用户资料和聊天记录检索"
  >
    <Card class="mb-4">
      <Space wrap>
        <Input.Search
          v-model:value="keyword"
          allow-clear
          enter-button="搜索"
          placeholder="搜索用户名 / 昵称 / 聊天记录 / Telegram ID"
          style="width: 420px"
          @search="loadData"
        />
        <Button
          type="primary"
          :disabled="!canRunCloudDanger"
          @click="openCreate"
        >
          添加 Telegram 登录账号
        </Button>
        <Button :loading="loading" @click="loadData">刷新</Button>
      </Space>
      <div class="mt-2 text-xs text-[var(--ant-color-text-description)]">
        当前先加载用户入口；聊天记录只在选中单个用户后读取，避免一次加载过多历史消息。
      </div>
    </Card>

    <Row :gutter="16">
      <Col :xl="7" :span="24">
        <Card :loading="loading" title="登录账号登记">
          <List
            v-if="overview.accounts.length > 0"
            :data-source="overview.accounts"
          >
            <template #renderItem="{ item }">
              <List.Item>
                <List.Item.Meta
                  :description="`${item.phone || '-'} · ${item.tg_user_id ? `ID ${item.tg_user_id}` : '未填ID'} · ${item.username ? `@${item.username}` : '-'}`"
                  :title="item.label"
                />
                <Tag color="blue">{{ item.status }}</Tag>
              </List.Item>
            </template>
          </List>
          <Empty v-else description="暂无登录账号登记" />
        </Card>
      </Col>

      <Col :xl="7" :span="24">
        <Card :loading="loading" title="用户入口">
          <List v-if="overview.users.length > 0" :data-source="overview.users">
            <template #renderItem="{ item }">
              <List.Item class="cursor-pointer" @click="selectUser(item)">
                <List.Item.Meta
                  :description="`${usernameText(item)} · ${item.message_count} 条消息`"
                  :title="item.display_name"
                />
                <Tag
                  v-if="selectedUser?.tg_user_id === item.tg_user_id"
                  color="green"
                >
                  当前
                </Tag>
              </List.Item>
            </template>
          </List>
          <Empty v-else description="暂无 bot 用户" />
        </Card>
      </Col>

      <Col :xl="10" :span="24">
        <Card
          :loading="loading"
          :title="
            selectedUser
              ? `${selectedUser.display_name} 的聊天记录`
              : '聊天记录'
          "
        >
          <List
            v-if="selectedUser && messages.length > 0"
            :data-source="messages"
          >
            <template #renderItem="{ item }">
              <List.Item>
                <div
                  class="w-full rounded-lg p-3"
                  :class="
                    item.direction === 'out'
                      ? 'bg-blue-50 text-right'
                      : 'bg-gray-50'
                  "
                >
                  <div class="mb-1 text-xs text-gray-500">
                    {{ item.direction_label }} ·
                    {{
                      item.username_snapshot
                        ? `@${item.username_snapshot}`
                        : item.tg_user_id
                    }}
                    · {{ item.created_at || '-' }}
                  </div>
                  <div class="whitespace-pre-wrap break-words text-sm">
                    {{ item.text || `[${item.content_type}]` }}
                  </div>
                </div>
              </List.Item>
            </template>
          </List>
          <Empty
            v-else
            :description="selectedUser ? '暂无聊天记录' : '先选择左侧用户'"
          />
        </Card>
      </Col>
    </Row>

    <Modal
      v-model:open="open"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      title="添加 Telegram 登录账号"
      @ok="saveAccount"
    >
      <Form layout="vertical">
        <Form.Item label="账号备注" required>
          <Input v-model:value="form.label" placeholder="例如：客服一号" />
        </Form.Item>
        <Form.Item label="手机号">
          <Input v-model:value="form.phone" placeholder="可选，仅做登记" />
        </Form.Item>
        <Form.Item label="Telegram 用户ID">
          <Input
            v-model:value="form.tg_user_id"
            placeholder="可选；填写后该用户名可在代理列表绑定用户"
          />
        </Form.Item>
        <Form.Item label="用户名">
          <Input
            v-model:value="form.username"
            placeholder="例如：@shiyi4，多个用户名可用逗号分隔"
          />
        </Form.Item>
        <Form.Item label="备注">
          <Input.TextArea
            v-model:value="form.note"
            :rows="3"
            placeholder="授权状态、用途等"
          />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>
