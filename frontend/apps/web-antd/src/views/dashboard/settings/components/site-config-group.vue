<script lang="ts" setup>
import type {
  DashboardSiteConfigGroup,
  DashboardSiteConfigGroupItem,
  DashboardSiteConfigItem,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  message,
  Space,
  Switch,
  Tag,
} from 'ant-design-vue';
import QRCode from 'qrcode';

import {
  bindDashboardTotpApi,
  changeDashboardMyPasswordApi,
  getDashboardSiteConfigGroupsApi,
  getDashboardSiteConfigsApi,
  initDashboardSiteConfigsApi,
  startDashboardTotpBindApi,
  testDashboardDailyExpirySummaryApi,
  updateDashboardSiteConfigApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const props = defineProps<{
  description?: string;
  groupKey: string;
  showPasswordCard?: boolean;
  title: string;
}>();

const loading = ref(false);
const initLoading = ref(false);
const siteConfigs = ref<DashboardSiteConfigItem[]>([]);
const configGroups = ref<DashboardSiteConfigGroup[]>([]);
const savingMap = reactive<Record<string, boolean>>({});
const testSendingMap = reactive<Record<string, boolean>>({});
const draftMap = reactive<Record<string, string>>({});
const sensitiveMap = reactive<Record<string, boolean>>({});
const maskedMap = reactive<Record<string, boolean>>({});

const activeGroup = computed(
  () =>
    configGroups.value.find((item) => item.group === props.groupKey) || null,
);
const items = computed(() =>
  (activeGroup.value?.items || []).filter(
    (item) => item.key !== 'dashboard_totp_secret',
  ),
);
const totpItem = computed(
  () =>
    (activeGroup.value?.items || []).find(
      (item) => item.key === 'dashboard_totp_secret',
    ) || null,
);
const totpQrCode = ref('');
const totpSecret = ref('');
const totpToken = ref('');
const totpOldToken = ref('');
const totpGenerating = ref(false);
const totpBinding = ref(false);
const passwordSaving = ref(false);
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

function requireSettingsWrite(action: string) {
  return requireCloudDangerPermission(action);
}

function syncDrafts() {
  for (const item of items.value) {
    sensitiveMap[item.key] = !!item.is_sensitive;
    if (item.key === 'trongrid_api_key') {
      draftMap[item.key] = item.value || '';
      maskedMap[item.key] = false;
    } else if (item.is_sensitive) {
      const preview = item.value_preview || '';
      draftMap[item.key] = preview;
      maskedMap[item.key] = !!preview;
    } else {
      draftMap[item.key] = item.value || '';
      maskedMap[item.key] = false;
    }
  }
}

async function loadData() {
  loading.value = true;
  try {
    const [configs, groups] = await Promise.all([
      getDashboardSiteConfigsApi({ group: props.groupKey }),
      getDashboardSiteConfigGroupsApi({ group: props.groupKey }),
    ]);
    siteConfigs.value = configs;
    configGroups.value = groups;
    syncDrafts();
  } finally {
    loading.value = false;
  }
}

function currentConfig(item: DashboardSiteConfigGroupItem) {
  return siteConfigs.value.find((config) => config.key === item.key) || null;
}

async function initConfigs() {
  if (!requireSettingsWrite('初始化配置')) return;
  initLoading.value = true;
  try {
    await initDashboardSiteConfigsApi({ scope: 'configs' });
    message.success('配置项已初始化');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '初始化失败');
  } finally {
    initLoading.value = false;
  }
}

function activateSensitiveEdit(item: DashboardSiteConfigGroupItem) {
  if (!item.is_sensitive || !maskedMap[item.key]) {
    return;
  }
  draftMap[item.key] = '';
  maskedMap[item.key] = false;
}

async function generateTotpQrCode() {
  if (!requireSettingsWrite('绑定后台二级验证')) return;
  if (totpItem.value?.value_preview && !totpOldToken.value.trim()) {
    message.error(
      '更换 TOTP 密钥前，请先输入当前 Google Authenticator 的 6 位动态码',
    );
    return;
  }
  totpGenerating.value = true;
  try {
    const result = await startDashboardTotpBindApi({
      old_otp_token: totpItem.value?.value_preview
        ? totpOldToken.value.trim()
        : undefined,
    });
    totpSecret.value = result.secret;
    totpToken.value = '';
    totpQrCode.value = await QRCode.toDataURL(result.otpauthUrl, {
      errorCorrectionLevel: 'M',
      margin: 1,
      width: 220,
    });
    message.success(
      totpItem.value?.value_preview
        ? '已生成新的绑定二维码；完成校验后将更换旧 TOTP 密钥'
        : '二维码已生成，请用 Google Authenticator 扫码',
    );
  } catch (error: any) {
    message.error(error?.message || '生成二维码失败，请确认当前动态码是否正确');
  } finally {
    totpGenerating.value = false;
  }
}

async function savePassword() {
  passwordSaving.value = true;
  try {
    await changeDashboardMyPasswordApi({ ...passwordForm });
    message.success('密码修改成功，请重新登录');
    passwordForm.old_password = '';
    passwordForm.new_password = '';
    passwordForm.confirm_password = '';
  } catch (error: any) {
    message.error(error?.message || '密码修改失败');
  } finally {
    passwordSaving.value = false;
  }
}

async function bindTotp() {
  if (!requireSettingsWrite('保存后台二级验证')) return;
  if (!totpToken.value.trim()) {
    message.error('请输入 Google Authenticator 中显示的 6 位动态码');
    return;
  }
  totpBinding.value = true;
  try {
    await bindDashboardTotpApi({ otp_token: totpToken.value.trim() });
    message.success('Google 二级验证已绑定');
    totpQrCode.value = '';
    totpSecret.value = '';
    totpToken.value = '';
    totpOldToken.value = '';
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '动态码校验失败');
  } finally {
    totpBinding.value = false;
  }
}

const switchConfigKeys = new Set([
  'cloud_auto_renew_execution_notify_enabled',
  'cloud_daily_expiry_summary_enabled',
  'cloud_renew_notice_debug_repeat',
  'scanner_block_log_enabled',
  'scanner_verbose',
  'telegram_listener_push_enabled',
  'telegram_listener_push_private_enabled',
  'text_init_enabled',
]);

const textInputConfigKeys = new Set([
  'cleanup_retention_days',
  'cloud_asset_sync_interval_seconds',
  'cloud_auto_renew_execution_notify_events',
  'cloud_delete_after_days',
  'cloud_delete_time',
  'cloud_renew_notice_days',
  'cloud_suspend_after_days',
  'cloud_suspend_time',
  'cloud_unattached_ip_delete_after_days',
  'cloud_unattached_ip_delete_time',
  'fsm_data_ttl',
  'fsm_state_ttl',
  'redis_db',
  'redis_port',
]);

function isSwitchConfig(item: DashboardSiteConfigGroupItem) {
  return switchConfigKeys.has(item.key);
}

function isTextInputConfig(item: DashboardSiteConfigGroupItem) {
  return textInputConfigKeys.has(item.key);
}

function switchChecked(item: DashboardSiteConfigGroupItem) {
  return String(draftMap[item.key] || '').trim() === '1';
}

async function saveSwitchItem(
  item: DashboardSiteConfigGroupItem,
  checked: boolean,
) {
  if (!requireSettingsWrite('保存系统开关')) return;
  draftMap[item.key] = checked ? '1' : '0';
  await saveItem(item);
}

async function testDailyExpirySummary() {
  if (!requireSettingsWrite('测试每日到期汇总通知')) return;
  testSendingMap.cloud_daily_expiry_summary_enabled = true;
  try {
    const result = await testDashboardDailyExpirySummaryApi();
    message.success(
      `测试通知已发送：今日到期 ${result.today} 台，已到期 ${result.expired} 台`,
    );
  } catch (error: any) {
    message.error(error?.message || '测试发送失败');
  } finally {
    testSendingMap.cloud_daily_expiry_summary_enabled = false;
  }
}

async function saveItem(item: DashboardSiteConfigGroupItem) {
  if (!requireSettingsWrite('保存系统配置')) return;
  const current = currentConfig(item);
  if (!current?.id) {
    message.error('该配置尚未初始化，请先点击顶部“初始化配置”');
    return;
  }
  const value = draftMap[item.key] ?? '';
  const preserveExisting =
    item.key !== 'trongrid_api_key' &&
    !!item.is_sensitive &&
    (maskedMap[item.key] || !value.trim());
  savingMap[item.key] = true;
  try {
    await updateDashboardSiteConfigApi(current.id, {
      is_sensitive: !!sensitiveMap[item.key],
      key: item.key,
      preserve_existing: preserveExisting,
      value: preserveExisting ? '' : value,
    });
    message.success(
      preserveExisting
        ? `已保留原密钥：${item.description || item.key}`
        : `已保存：${item.description || item.key}`,
    );
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    savingMap[item.key] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page :description="description || ''" :title="title">
    <Space class="mb-4">
      <Button
        type="primary"
        :disabled="!canRunCloudDanger"
        :loading="initLoading"
        @click="initConfigs"
      >
        初始化配置
      </Button>
      <Button :loading="loading" @click="loadData">刷新</Button>
    </Space>

    <Card v-if="props.showPasswordCard" class="mb-4" :bordered="false">
      <div class="config-title mb-3">后台密码设置</div>
      <Form layout="vertical">
        <Form.Item label="旧密码">
          <Input.Password
            v-model:value="passwordForm.old_password"
            :visibility-toggle="true"
            placeholder="请输入旧密码"
          />
        </Form.Item>
        <Form.Item label="新密码">
          <Input.Password
            v-model:value="passwordForm.new_password"
            :visibility-toggle="true"
            placeholder="请输入新密码"
          />
        </Form.Item>
        <Form.Item label="确认新密码">
          <Input.Password
            v-model:value="passwordForm.confirm_password"
            :visibility-toggle="true"
            placeholder="再次输入新密码"
          />
        </Form.Item>
        <Button type="primary" :loading="passwordSaving" @click="savePassword">
          保存新密码
        </Button>
      </Form>
    </Card>

    <Card v-if="totpItem" class="mb-4" :bordered="false">
      <div class="totp-head">
        <div>
          <div class="config-title">
            {{ totpItem.description || '后台 Google Authenticator 二级验证' }}
          </div>
          <div class="config-desc">
            {{
              totpItem.value_preview
                ? '已绑定二级验证。更换密钥时必须先输入当前/旧 Google Authenticator 动态码；旧码验证通过后才会生成新二维码。新动态码校验成功后才会覆盖旧密钥，旧绑定将失效。'
                : '生成二维码后，用 Google Authenticator 扫码，再输入 6 位动态码完成绑定。'
            }}
          </div>
        </div>
        <Tag :color="totpItem.value_preview ? 'green' : 'default'">
          {{ totpItem.value_preview ? '已绑定' : '未绑定' }}
        </Tag>
      </div>
      <Alert
        class="mb-4"
        show-icon
        type="info"
        :message="
          totpItem.value_preview
            ? '更换密钥必须先验证当前/旧 Google Authenticator 动态码；验证通过后才会生成新二维码。新动态码校验保存后，旧密钥和旧动态码将不能再登录。'
            : '密钥只用于本次绑定；动态码校验通过后才会加密写入后台配置。'
        "
      />
      <Space class="mb-4">
        <Input
          v-if="totpItem.value_preview"
          v-model:value="totpOldToken"
          autocomplete="one-time-code"
          inputmode="numeric"
          :maxlength="6"
          placeholder="先输入当前/旧验证器 6 位动态码"
          style="width: 260px"
        />
        <Button
          type="primary"
          :disabled="!canRunCloudDanger"
          :loading="totpGenerating"
          @click="generateTotpQrCode"
        >
          {{
            totpItem.value_preview ? '验证旧码并生成新二维码' : '生成绑定二维码'
          }}
        </Button>
      </Space>
      <div v-if="totpQrCode" class="totp-bind-box">
        <img class="totp-qrcode" :src="totpQrCode" alt="TOTP QR Code" />
        <div class="totp-bind-form">
          <div class="config-desc mb-2">
            不能扫码时，可手动输入新密钥：{{ totpSecret }}
          </div>
          <Input
            v-model:value="totpToken"
            class="mb-3"
            autocomplete="one-time-code"
            inputmode="numeric"
            :maxlength="6"
            placeholder="输入新 Google Authenticator 6 位动态码"
          />
          <Button
            type="primary"
            :disabled="!canRunCloudDanger"
            :loading="totpBinding"
            @click="bindTotp"
          >
            校验新码并保存
          </Button>
        </div>
      </div>
    </Card>

    <div v-if="items.length > 0" class="config-list">
      <div v-for="item in items" :key="item.key" class="config-row">
        <div class="config-head">
          <div>
            <div class="config-title">{{ item.description || item.key }}</div>
          </div>
          <Space>
            <Button
              type="primary"
              :disabled="!canRunCloudDanger"
              :loading="savingMap[item.key]"
              @click="saveItem(item)"
            >
              保存
            </Button>
          </Space>
        </div>
        <Input.TextArea
          v-if="item.key === 'trongrid_api_key'"
          v-model:value="draftMap[item.key]"
          :auto-size="{ minRows: 3, maxRows: 8 }"
          placeholder="多个 Key 请每行一个，或用逗号/分号分隔"
        />
        <div v-else-if="isSwitchConfig(item)" class="switch-row">
          <Switch
            :checked="switchChecked(item)"
            checked-children="开启"
            :disabled="!canRunCloudDanger"
            un-checked-children="关闭"
            :loading="savingMap[item.key]"
            @change="(checked) => saveSwitchItem(item, Boolean(checked))"
          />
          <span class="switch-value">
            当前：{{ switchChecked(item) ? '开启' : '关闭' }}
          </span>
          <Button
            v-if="item.key === 'cloud_daily_expiry_summary_enabled'"
            :disabled="!canRunCloudDanger || !switchChecked(item)"
            :loading="testSendingMap[item.key]"
            @click="testDailyExpirySummary"
          >
            测试发送
          </Button>
        </div>
        <Input
          v-else-if="isTextInputConfig(item)"
          v-model:value="draftMap[item.key]"
          :placeholder="item.value || '请输入配置内容'"
        />
        <Input
          v-else-if="item.is_sensitive"
          v-model:value="draftMap[item.key]"
          :placeholder="item.value_preview || '请输入配置内容'"
          @focus="activateSensitiveEdit(item)"
        />
        <Input.TextArea
          v-else
          v-model:value="draftMap[item.key]"
          :auto-size="{ minRows: 2, maxRows: 5 }"
          :placeholder="item.value || '请输入配置内容'"
        />
      </div>
    </div>

    <div v-else class="empty-hint">暂无配置项，请先点击“初始化配置”。</div>
  </Page>
</template>

<style scoped>
.config-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-row {
  padding: 16px;
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.config-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
}

.config-desc {
  margin-top: 4px;
  color: rgb(107 114 128);
}

.totp-head {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.totp-bind-box {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
}

.totp-qrcode {
  width: 220px;
  height: 220px;
  padding: 8px;
  background: #fff;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 12px;
}

.totp-bind-form {
  flex: 1;
  min-width: 260px;
}

.switch-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.switch-value {
  color: rgb(107 114 128);
}

.empty-hint {
  color: rgb(107 114 128);
}
</style>
