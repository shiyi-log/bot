<script lang="ts" setup>
import type {
  DashboardTelegramAccountsOverview,
  DashboardTelegramLoginAccountItem,
} from '#/api/admin';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Empty,
  Form,
  Input,
  List,
  message,
  Modal,
  Space,
  Steps,
  Switch,
  Tag,
} from 'ant-design-vue';

import {
  checkDashboardTelegramAccountStatusApi,
  getDashboardTelegramAccountsApi,
  startDashboardTelegramLoginApi,
  submitDashboardTelegramLoginCodeApi,
  submitDashboardTelegramLoginPasswordApi,
  updateDashboardTelegramAccountNotifyApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const checkingAccountIds = ref<number[]>([]);
const open = ref(false);
const loginStep = ref(0);
const overview = ref<DashboardTelegramAccountsOverview>({
  accounts: [],
  chats: [],
  messages: [],
  users: [],
});

const accountId = ref<null | number>(null);
const form = reactive({
  code: '',
  password: '',
  phone: '',
});

const stepTitle = ['输入手机号', '输入验证码', '输入二级密码'];
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const statusTextMap: Record<string, string> = {
  code_sent: '验证码已发送',
  error: '登录失败',
  logged_in: '登录成功',
  listener_error: '监听异常',
  password_required: '等待二级密码',
  pending: '待处理',
  registered: '已登记',
  session_expired: '会话失效',
};

function statusText(status: string) {
  return statusTextMap[status] || status || '-';
}

function statusColor(status: string) {
  if (['code_sent', 'password_required', 'pending'].includes(status)) {
    return 'warning';
  }
  if (['error', 'listener_error', 'session_expired'].includes(status)) {
    return 'error';
  }
  return status === 'logged_in' ? 'success' : 'blue';
}

async function loadData() {
  loading.value = true;
  try {
    overview.value = await getDashboardTelegramAccountsApi({
      scope: 'accounts',
    });
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireCloudDangerPermission('登录 Telegram 账号')) return;
  form.phone = '';
  form.code = '';
  form.password = '';
  loginStep.value = 0;
  accountId.value = null;
  open.value = true;
}

function needsRelogin(account: DashboardTelegramLoginAccountItem) {
  return [
    'code_sent',
    'error',
    'listener_error',
    'password_required',
    'session_expired',
  ].includes(account.status);
}

function reloginButtonText(account: DashboardTelegramLoginAccountItem) {
  return ['code_sent', 'password_required'].includes(account.status)
    ? '继续登录'
    : '重新登录';
}

function openRelogin(account: DashboardTelegramLoginAccountItem) {
  if (!requireCloudDangerPermission('重新登录 Telegram 账号')) return;
  form.phone = account.phone || '';
  form.code = '';
  form.password = '';
  if (account.status === 'code_sent') {
    loginStep.value = 1;
    accountId.value = account.id;
  } else if (account.status === 'password_required') {
    loginStep.value = 2;
    accountId.value = account.id;
  } else {
    loginStep.value = 0;
    accountId.value = null;
  }
  open.value = true;
}

async function checkAccountStatus(account: DashboardTelegramLoginAccountItem) {
  if (!requireCloudDangerPermission('检查 Telegram 账号状态')) return;
  checkingAccountIds.value = [...checkingAccountIds.value, account.id];
  try {
    const updated = await checkDashboardTelegramAccountStatusApi(account.id);
    const index = overview.value.accounts.findIndex(
      (item) => item.id === updated.id,
    );
    if (index !== -1) {
      overview.value.accounts = [
        ...overview.value.accounts.slice(0, index),
        updated,
        ...overview.value.accounts.slice(index + 1),
      ];
    }
    message.success(
      needsRelogin(updated) ? '账号状态异常，请重新登录' : '账号状态正常',
    );
  } catch (error: any) {
    message.error(error?.message || '状态检查失败');
  } finally {
    checkingAccountIds.value = checkingAccountIds.value.filter(
      (id) => id !== account.id,
    );
  }
}

async function handleLoginStep() {
  if (!requireCloudDangerPermission('登录 Telegram 账号')) return;
  if (saving.value) return;
  if (loginStep.value === 0) {
    if (!String(form.phone || '').trim()) {
      message.error('请输入手机号');
      return;
    }
    saving.value = true;
    try {
      const result = await startDashboardTelegramLoginApi({
        phone: form.phone,
      });
      accountId.value = result.account_id;
      message.success('验证码已发送');
      loginStep.value = 1;
    } catch (error: any) {
      message.error(error?.message || '发送验证码失败');
    } finally {
      saving.value = false;
    }
    return;
  }
  if (loginStep.value === 1) {
    if (!String(form.code || '').trim()) {
      message.error('请输入验证码');
      return;
    }
    if (!accountId.value) {
      message.error('登录会话不存在，请重新输入手机号');
      loginStep.value = 0;
      return;
    }
    saving.value = true;
    try {
      const result = await submitDashboardTelegramLoginCodeApi({
        account_id: accountId.value,
        code: form.code,
      });
      if (result.requires_password) {
        loginStep.value = 2;
      } else {
        message.success('登录成功');
        open.value = false;
        await loadData();
      }
    } catch (error: any) {
      message.error(error?.message || '验证码登录失败');
    } finally {
      saving.value = false;
    }
    return;
  }
  if (!accountId.value) {
    message.error('登录会话不存在，请重新输入手机号');
    loginStep.value = 0;
    return;
  }
  saving.value = true;
  try {
    await submitDashboardTelegramLoginPasswordApi({
      account_id: accountId.value,
      password: form.password,
    });
    message.success('登录成功');
    open.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '二级密码登录失败');
  } finally {
    saving.value = false;
  }
}

async function resendCode() {
  if (!requireCloudDangerPermission('重新发送 Telegram 验证码')) return;
  if (saving.value) return;
  if (!String(form.phone || '').trim()) {
    message.error('手机号不能为空');
    loginStep.value = 0;
    return;
  }
  saving.value = true;
  try {
    const result = await startDashboardTelegramLoginApi({
      phone: form.phone,
    });
    accountId.value = result.account_id;
    form.code = '';
    loginStep.value = 1;
    message.success('验证码已重新发送');
  } catch (error: any) {
    message.error(error?.message || '重新发送验证码失败');
  } finally {
    saving.value = false;
  }
}

async function toggleNotify(accountId: number, notifyEnabled: boolean) {
  if (!requireCloudDangerPermission('修改 Telegram 账号通知')) {
    await loadData();
    return;
  }
  try {
    await updateDashboardTelegramAccountNotifyApi(accountId, {
      notify_enabled: notifyEnabled,
    });
    message.success(notifyEnabled ? '已开启通知' : '已关闭通知');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '更新通知开关失败');
    await loadData();
  }
}

async function toggleListenerPush(
  accountId: number,
  listenerPushEnabled: boolean,
) {
  if (!requireCloudDangerPermission('修改 Telegram 监听推送')) {
    await loadData();
    return;
  }
  try {
    await updateDashboardTelegramAccountNotifyApi(accountId, {
      listener_push_enabled: listenerPushEnabled,
    });
    message.success(listenerPushEnabled ? '已开启监听推送' : '已关闭监听推送');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '更新监听推送开关失败');
    await loadData();
  }
}

function prevLoginStep() {
  if (loginStep.value > 0) loginStep.value -= 1;
}

onMounted(loadData);
</script>

<template>
  <Page title="账号列表" description="管理 Telegram 登录账号">
    <Card class="mb-4">
      <Space wrap>
        <Button
          type="primary"
          :disabled="!canRunCloudDanger"
          @click="openCreate"
        >
          登录
        </Button>
        <Button :loading="loading" @click="loadData">刷新</Button>
      </Space>
      <div class="mt-2 text-xs text-[var(--ant-color-text-description)]">
        自动识别范围：用户主动与 bot 产生的资料。个人 Telegram
        账号登录采集需要单独授权流程。
      </div>
    </Card>

    <Card :loading="loading" title="账号列表">
      <List
        v-if="overview.accounts.length > 0"
        :data-source="overview.accounts"
      >
        <template #renderItem="{ item }">
          <List.Item>
            <List.Item.Meta
              :description="`${item.phone || '-'} · ${item.tg_user_id ? `ID ${item.tg_user_id}` : '未填ID'} · ${item.username ? `@${item.username}` : '-'} · ${item.note || ''}`"
              :title="item.label"
            />
            <Space>
              <span class="text-xs text-[var(--ant-color-text-description)]">通知</span>
              <Switch
                size="small"
                :disabled="!canRunCloudDanger"
                :checked="item.notify_enabled"
                @change="(checked) => toggleNotify(item.id, !!checked)"
              />
              <span class="text-xs text-[var(--ant-color-text-description)]">监听推送</span>
              <Switch
                size="small"
                :disabled="!canRunCloudDanger"
                :checked="item.listener_push_enabled"
                @change="(checked) => toggleListenerPush(item.id, !!checked)"
              />
              <Tag :color="statusColor(item.status)">
                {{ statusText(item.status) }}
              </Tag>
              <Button
                v-if="needsRelogin(item)"
                size="small"
                type="primary"
                danger
                :disabled="!canRunCloudDanger"
                @click="openRelogin(item)"
              >
                {{ reloginButtonText(item) }}
              </Button>
              <Button
                v-else
                size="small"
                :disabled="!canRunCloudDanger"
                :loading="checkingAccountIds.includes(item.id)"
                @click="checkAccountStatus(item)"
              >
                状态检查
              </Button>
            </Space>
          </List.Item>
        </template>
      </List>
      <Empty v-else description="暂无账号" />
    </Card>

    <Modal
      v-model:open="open"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      :ok-text="loginStep < 2 ? '下一步' : '确定'"
      title="登录 Telegram 账号"
      @ok="handleLoginStep"
    >
      <Steps
        class="mb-5"
        size="small"
        :current="loginStep"
        :items="stepTitle.map((title) => ({ title }))"
      />
      <Form layout="vertical">
        <Form.Item v-if="loginStep === 0" label="手机号" required>
          <Input
            v-model:value="form.phone"
            placeholder="请输入 Telegram 手机号，例如 +8613800000000"
          />
        </Form.Item>
        <Form.Item v-if="loginStep === 1" label="验证码" required>
          <Input
            v-model:value="form.code"
            placeholder="请输入 Telegram 验证码"
          />
        </Form.Item>
        <Form.Item v-if="loginStep === 2" label="二级密码">
          <Input.Password
            v-model:value="form.password"
            placeholder="可为空，直接点确定"
            :visibility-toggle="false"
          />
          <div class="mt-2 text-xs text-[var(--ant-color-text-description)]">
            二级密码允许为空；为空时直接点确定。
          </div>
        </Form.Item>
      </Form>
      <template #footer>
        <Space>
          <Button v-if="loginStep > 0" @click="prevLoginStep">上一步</Button>
          <Button
            v-if="loginStep === 1"
            :disabled="saving"
            :loading="saving"
            @click="resendCode"
          >
            重新发送验证码
          </Button>
          <Button @click="open = false">取消</Button>
          <Button
            type="primary"
            :disabled="!canRunCloudDanger"
            :loading="saving"
            @click="handleLoginStep"
          >
            {{ loginStep < 2 ? '下一步' : '确定' }}
          </Button>
        </Space>
      </template>
    </Modal>
  </Page>
</template>
