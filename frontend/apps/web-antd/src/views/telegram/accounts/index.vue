<script lang="ts" setup>
import type { TelegramLoginAccount } from '#/api/telegram';
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Input,
  Modal,
  Popconfirm,
  Space,
  Steps,
  Table,
  Tag,
  message,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  checkTelegramLoginAccountApi,
  deleteTelegramLoginAccountApi,
  getTelegramLoginAccountsApi,
  startTelegramLoginApi,
  submitTelegramLoginCodeApi,
  submitTelegramLoginPasswordApi,
} from '#/api/telegram';

interface RequestError {
  message?: string;
  response?: {
    data?: Record<string, unknown>;
    status?: number;
  };
}

const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const loginStep = ref(0);
const accountId = ref<null | number>(null);
const checkingAccountIds = ref<number[]>([]);
const keyword = ref('');
const accounts = ref<TelegramLoginAccount[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
const loginForm = reactive({
  code: '',
  label: '',
  password: '',
  phone: '',
});

const columns: TableColumnsType<TelegramLoginAccount> = [
  {
    title: '标签',
    dataIndex: 'label',
    key: 'label',
    fixed: 'left',
    width: 160,
  },
  { title: '手机号', dataIndex: 'phone', key: 'phone', width: 170 },
  {
    title: 'Telegram ID',
    dataIndex: 'telegram_id',
    key: 'telegram_id',
    width: 170,
  },
  { title: '用户名', dataIndex: 'username', key: 'username', width: 150 },
  { title: '姓名', key: 'name', width: 160 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 140 },
  {
    title: '最近错误',
    dataIndex: 'last_error',
    key: 'last_error',
    ellipsis: true,
    width: 260,
  },
  {
    title: '最近检查',
    dataIndex: 'last_checked_at',
    key: 'last_checked_at',
    width: 180,
  },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', fixed: 'right', width: 260 },
];

const loginSteps = [
  { title: '手机号' },
  { title: '验证码' },
  { title: '二级密码' },
];

const statusTextMap: Record<string, string> = {
  code_sent: '等待验证码',
  error: '登录失败',
  logged_in: '已登录',
  password_required: '等待二级密码',
  pending: '处理中',
  session_expired: '会话失效',
};

function statusText(status: string) {
  return statusTextMap[status] || status || '-';
}

function statusColor(status: string) {
  if (status === 'logged_in') return 'success';
  if (['code_sent', 'password_required', 'pending'].includes(status)) {
    return 'warning';
  }
  return 'error';
}

function asTelegramAccount(record: unknown) {
  return record as TelegramLoginAccount;
}

function displayName(account: TelegramLoginAccount) {
  return (
    [account.first_name, account.last_name].filter(Boolean).join(' ') || '-'
  );
}

function formatDate(value: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function requestErrorMessage(error: unknown, fallback: string) {
  const requestError = error as RequestError;
  const detail = requestError.response?.data?.detail;
  return typeof detail === 'string' && detail.trim() ? detail : fallback;
}

function isConflict(error: unknown) {
  return (error as RequestError).response?.status === 409;
}

async function loadAccounts() {
  loading.value = true;
  try {
    const result = await getTelegramLoginAccountsApi({
      page: pagination.page,
      page_size: pagination.pageSize,
      search: keyword.value.trim(),
    });
    accounts.value = result.results;
    pagination.total = result.count;
  } catch (error) {
    message.error(requestErrorMessage(error, '加载 Telegram 账号失败'));
  } finally {
    loading.value = false;
  }
}

function resetLoginForm() {
  Object.assign(loginForm, { code: '', label: '', password: '', phone: '' });
  accountId.value = null;
  loginStep.value = 0;
}

function openLogin() {
  resetLoginForm();
  modalOpen.value = true;
}

function openRelogin(account: TelegramLoginAccount) {
  resetLoginForm();
  Object.assign(loginForm, {
    code: '',
    label: account.label,
    password: '',
    phone: account.phone,
  });
  accountId.value = account.id;
  if (account.status === 'code_sent') {
    loginStep.value = 1;
  } else if (account.status === 'password_required') {
    loginStep.value = 2;
  } else {
    accountId.value = null;
    loginStep.value = 0;
  }
  modalOpen.value = true;
}

function reloginText(account: TelegramLoginAccount) {
  return ['code_sent', 'password_required'].includes(account.status)
    ? '继续登录'
    : '重新登录';
}

function closeLoginModal() {
  if (saving.value) return;
  modalOpen.value = false;
}

function previousLoginStep() {
  if (saving.value || loginStep.value === 0) return;
  loginStep.value = 0;
  accountId.value = null;
  loginForm.code = '';
  loginForm.password = '';
}

function validInternationalPhone(phone: string) {
  const digits = phone.replace(/\D/g, '');
  return (
    /^\+[\d\s()-]+$/.test(phone) && digits.length >= 8 && digits.length <= 15
  );
}

async function finishLogin() {
  message.success('Telegram 账号登录成功');
  await loadAccounts();
  modalOpen.value = false;
}

async function startLogin(resending = false) {
  const phone = loginForm.phone.trim();
  if (!validInternationalPhone(phone)) {
    message.error('请输入以 + 开头的国际格式手机号，例如 +8613812345678');
    return;
  }
  if (saving.value) return;
  saving.value = true;
  try {
    const result = await startTelegramLoginApi({
      label: loginForm.label.trim() || undefined,
      phone,
    });
    accountId.value = result.account_id;
    loginForm.phone = result.account.phone;
    loginForm.code = '';
    loginStep.value = 1;
    await loadAccounts();
    message.success(resending ? '验证码已重新发送' : '验证码已发送');
  } catch (error) {
    if (isConflict(error)) {
      message.error('当前登录请求正在处理中，请稍后刷新账号状态后再试');
    } else {
      message.error(
        requestErrorMessage(
          error,
          resending ? '重新发送验证码失败' : '发送验证码失败',
        ),
      );
    }
  } finally {
    saving.value = false;
  }
}

async function submitCode() {
  if (!loginForm.code.trim()) {
    message.error('请输入验证码');
    return;
  }
  if (!accountId.value) {
    message.error('登录会话不存在，请返回手机号步骤重新开始');
    return;
  }
  if (saving.value) return;
  saving.value = true;
  try {
    const result = await submitTelegramLoginCodeApi({
      account_id: accountId.value,
      code: loginForm.code.trim(),
    });
    accountId.value = result.account_id;
    if (result.next_step === 'password') {
      loginStep.value = 2;
      message.info('该账号已启用二级密码，请继续输入');
    } else {
      await finishLogin();
    }
  } catch (error) {
    message.error(requestErrorMessage(error, '验证码登录失败'));
  } finally {
    saving.value = false;
  }
}

async function submitPassword() {
  if (!loginForm.password) {
    message.error('请输入二级密码');
    return;
  }
  if (!accountId.value) {
    message.error('登录会话不存在，请返回手机号步骤重新开始');
    return;
  }
  if (saving.value) return;
  saving.value = true;
  try {
    await submitTelegramLoginPasswordApi({
      account_id: accountId.value,
      password: loginForm.password,
    });
    await finishLogin();
  } catch (error) {
    message.error(requestErrorMessage(error, '二级密码登录失败'));
  } finally {
    saving.value = false;
  }
}

function submitLoginStep() {
  if (loginStep.value === 0) return startLogin();
  if (loginStep.value === 1) return submitCode();
  return submitPassword();
}

async function checkAccount(account: TelegramLoginAccount) {
  if (account.status !== 'logged_in') return;
  if (checkingAccountIds.value.includes(account.id)) return;
  checkingAccountIds.value = [...checkingAccountIds.value, account.id];
  try {
    const updated = await checkTelegramLoginAccountApi(account.id);
    const index = accounts.value.findIndex((item) => item.id === updated.id);
    if (index >= 0) accounts.value.splice(index, 1, updated);
    message.success(
      updated.status === 'logged_in'
        ? '账号状态正常'
        : '账号状态已更新，请按提示重新登录',
    );
  } catch (error) {
    message.error(requestErrorMessage(error, '账号状态检查失败'));
  } finally {
    checkingAccountIds.value = checkingAccountIds.value.filter(
      (id) => id !== account.id,
    );
  }
}

async function removeAccount(id: number) {
  try {
    await deleteTelegramLoginAccountApi(id);
    message.success('本地 Telegram 账号记录已删除');
    if (accounts.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1;
    }
    await loadAccounts();
  } catch (error) {
    message.error(requestErrorMessage(error, '删除本地账号记录失败'));
  }
}

function search() {
  pagination.page = 1;
  loadAccounts();
}

function handleTableChange(next: TablePaginationConfig) {
  pagination.page = next.current || 1;
  pagination.pageSize = next.pageSize || 20;
  loadAccounts();
}

function showTotal(total: number) {
  return `共 ${total} 个账号`;
}

onMounted(loadAccounts);
</script>

<template>
  <Page
    description="管理本地保存的 Telegram 用户账号登录会话"
    title="Telegram 账号"
  >
    <Alert
      class="mb-4"
      message="登录前请先在“运行设置”配置 Telegram API ID 和 API Hash；服务端还必须显式设置 ENABLE_TELEGRAM_ACCOUNT_NETWORK=1。页面不会显示或控制真实网络开关。"
      show-icon
      type="info"
    />
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>账号列表</span>
          <Space wrap>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索标签、手机号、用户名或姓名"
              style="width: 320px"
              @search="search"
            />
            <Button :loading="loading" @click="loadAccounts">刷新</Button>
            <Button type="primary" @click="openLogin">登录账号</Button>
          </Space>
        </div>
      </template>

      <Table
        :columns="columns"
        :data-source="accounts"
        :loading="loading"
        :pagination="{
          current: pagination.page,
          pageSize: pagination.pageSize,
          showSizeChanger: true,
          showTotal,
          total: pagination.total,
        }"
        :scroll="{ x: 1800 }"
        row-key="id"
        sticky
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'telegram_id'">
            {{ record.telegram_id ?? '-' }}
          </template>
          <template v-else-if="column.key === 'username'">
            {{ record.username ? `@${record.username}` : '-' }}
          </template>
          <template v-else-if="column.key === 'name'">
            {{ displayName(asTelegramAccount(record)) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="statusColor(record.status)">
              {{ statusText(record.status) }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'last_error'">
            <span :title="record.last_error">{{
              record.last_error || '-'
            }}</span>
          </template>
          <template v-else-if="column.key === 'last_checked_at'">
            {{ formatDate(record.last_checked_at) }}
          </template>
          <template v-else-if="column.key === 'updated_at'">
            {{ formatDate(record.updated_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button
                size="small"
                type="link"
                @click="openRelogin(asTelegramAccount(record))"
              >
                {{ reloginText(asTelegramAccount(record)) }}
              </Button>
              <Button
                v-if="record.status === 'logged_in'"
                :loading="checkingAccountIds.includes(record.id)"
                size="small"
                type="link"
                @click="checkAccount(asTelegramAccount(record))"
              >
                状态检查
              </Button>
              <Popconfirm
                cancel-text="取消"
                ok-text="只删除本地记录"
                title="仅删除本地保存的账号和会话，不会删除 Telegram 账号。确认继续？"
                @confirm="removeAccount(record.id)"
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
      :closable="!saving"
      :keyboard="!saving"
      :mask-closable="!saving"
      title="登录 Telegram 账号"
      @after-close="resetLoginForm"
      @cancel="closeLoginModal"
    >
      <Steps
        :current="loginStep"
        :items="loginSteps"
        class="mb-6"
        size="small"
      />

      <div v-if="loginStep === 0" class="space-y-4">
        <div>
          <div class="mb-1">账号标签（可选）</div>
          <Input
            v-model:value="loginForm.label"
            :maxlength="128"
            placeholder="例如：客服主账号"
            @press-enter="submitLoginStep"
          />
        </div>
        <div>
          <div class="mb-1">国际格式手机号</div>
          <Input
            v-model:value="loginForm.phone"
            autocomplete="tel"
            placeholder="例如 +8613812345678"
            @press-enter="submitLoginStep"
          />
          <div class="mt-1 text-xs text-[var(--ant-color-text-description)]">
            必须包含国家或地区代码，并以 + 开头。
          </div>
        </div>
      </div>

      <div v-else-if="loginStep === 1">
        <div class="mb-1">Telegram 验证码</div>
        <Input
          v-model:value="loginForm.code"
          autocomplete="one-time-code"
          placeholder="请输入 Telegram 收到的验证码"
          @press-enter="submitLoginStep"
        />
        <div class="mt-2 text-xs text-[var(--ant-color-text-description)]">
          验证码已发送至 {{ loginForm.phone }}。未收到时可重新发送。
        </div>
      </div>

      <div v-else>
        <div class="mb-1">Telegram 二级密码</div>
        <Input.Password
          v-model:value="loginForm.password"
          :visibility-toggle="false"
          autocomplete="current-password"
          placeholder="请输入该账号的二级密码"
          @press-enter="submitLoginStep"
        />
      </div>

      <template #footer>
        <Space>
          <Button :disabled="saving" @click="closeLoginModal">取消</Button>
          <Button
            v-if="loginStep > 0"
            :disabled="saving"
            @click="previousLoginStep"
          >
            上一步
          </Button>
          <Button
            v-if="loginStep === 1"
            :disabled="saving"
            @click="startLogin(true)"
          >
            重新发送
          </Button>
          <Button :loading="saving" type="primary" @click="submitLoginStep">
            {{
              loginStep === 0 ? '发送验证码' : loginStep === 1 ? '验证' : '登录'
            }}
          </Button>
        </Space>
      </template>
    </Modal>
  </Page>
</template>
