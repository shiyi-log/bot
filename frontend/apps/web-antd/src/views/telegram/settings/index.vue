<script lang="ts" setup>
import type { BotSettings, BotSettingsUpdate } from '#/api/telegram';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Form,
  FormItem,
  Input,
  InputNumber,
  Space,
  Switch,
  Tag,
  message,
} from 'ant-design-vue';

import { getBotSettingsApi, updateBotSettingsApi } from '#/api/telegram';

interface BotSettingsForm extends BotSettings {
  telegram_api_hash: string;
}

const loading = ref(false);
const saving = ref(false);
const apiKeyDirty = ref(false);
const apiIdDirty = ref(false);
const telegramApiHashDirty = ref(false);
const form = reactive<BotSettingsForm>({
  telegram_api_hash_configured: false,
  telegram_api_hash_preview: '',
  telegram_api_hash: '',
  telegram_api_id: '',
  tron_api_key_configured: false,
  tron_api_key_env_var: 'TRONGRID_API_KEY',
  tron_api_key_preview: '',
  tron_api_key: '',
  tron_api_url: 'https://api.trongrid.io',
  tron_monitor_enabled: false,
  tron_poll_interval: 30,
  updated_at: null,
});
const apiKeyInput = computed({
  get: () => form.tron_api_key ?? '',
  set: (value: string) => {
    form.tron_api_key = value;
    apiKeyDirty.value = true;
  },
});
const telegramApiIdInput = computed({
  get: () => form.telegram_api_id,
  set: (value: string) => {
    form.telegram_api_id = value;
    apiIdDirty.value = true;
  },
});
const telegramApiHashInput = computed({
  get: () => form.telegram_api_hash ?? '',
  set: (value: string) => {
    form.telegram_api_hash = value;
    telegramApiHashDirty.value = true;
  },
});

async function loadSettings() {
  loading.value = true;
  try {
    Object.assign(form, await getBotSettingsApi());
    form.telegram_api_hash = '';
    form.tron_api_key = '';
    apiIdDirty.value = false;
    telegramApiHashDirty.value = false;
    apiKeyDirty.value = false;
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  saving.value = true;
  try {
    const payload: BotSettingsUpdate = {
      tron_api_key_env_var: form.tron_api_key_env_var.trim(),
      tron_api_url: form.tron_api_url.trim().replace(/\/$/, ''),
      tron_monitor_enabled: form.tron_monitor_enabled,
      tron_poll_interval: form.tron_poll_interval,
    };
    if (apiKeyDirty.value) {
      payload.tron_api_key = form.tron_api_key;
    }
    if (telegramApiHashDirty.value) {
      payload.telegram_api_hash = form.telegram_api_hash;
    }
    if (apiIdDirty.value) {
      payload.telegram_api_id = form.telegram_api_id.trim();
    }
    Object.assign(form, await updateBotSettingsApi(payload));
    form.telegram_api_hash = '';
    form.tron_api_key = '';
    apiIdDirty.value = false;
    telegramApiHashDirty.value = false;
    apiKeyDirty.value = false;
    message.success('设置已保存');
  } finally {
    saving.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <Page
    description="配置 Telegram 账号登录与 TRON 只读监控参数"
    title="运行设置"
  >
    <Form
      :label-col="{ span: 5 }"
      :model="form"
      :wrapper-col="{ span: 15 }"
      @finish="saveSettings"
    >
      <Card :loading="loading" class="mb-4 max-w-4xl" title="Telegram API">
        <FormItem
          label="Telegram API ID"
          name="telegram_api_id"
          :rules="[
            {
              pattern: /^[1-9]\d*$/,
              message: 'API ID 必须是正整数，留空时使用环境变量',
            },
          ]"
        >
          <Input
            v-model:value="telegramApiIdInput"
            inputmode="numeric"
            placeholder="留空时使用 TELEGRAM_API_ID"
          />
        </FormItem>
        <FormItem label="Telegram API Hash" name="telegram_api_hash">
          <Input.Password
            v-model:value="telegramApiHashInput"
            :visibility-toggle="false"
            autocomplete="new-password"
            placeholder="仅写入；留空且未修改时保留现有配置"
          />
          <div class="mt-2 text-sm text-gray-500">
            当前预览：{{ form.telegram_api_hash_preview || '未配置' }}
          </div>
        </FormItem>
        <FormItem label="API Hash 状态">
          <Tag
            :color="form.telegram_api_hash_configured ? 'success' : 'warning'"
          >
            {{ form.telegram_api_hash_configured ? '已配置' : '未配置' }}
          </Tag>
        </FormItem>
        <Alert
          message="数据库中的 Telegram API ID 和 API Hash 优先，未配置时分别回退到 TELEGRAM_API_ID 与 TELEGRAM_API_HASH 环境变量。真实账号登录还要求服务端设置 ENABLE_TELEGRAM_ACCOUNT_NETWORK=1；前端不显示或控制该网络开关。"
          show-icon
          type="info"
        />
      </Card>

      <Card :loading="loading" class="max-w-4xl" title="TRON 监控">
        <FormItem label="启用 TRON 监控">
          <Switch v-model:checked="form.tron_monitor_enabled" />
        </FormItem>
        <FormItem
          label="TRON API 地址"
          name="tron_api_url"
          :rules="[
            { required: true, message: '请输入 TRON API 地址' },
            { type: 'url', message: '请输入完整的 http 或 https 地址' },
          ]"
        >
          <Input
            v-model:value="form.tron_api_url"
            placeholder="https://api.trongrid.io"
          />
        </FormItem>
        <FormItem
          label="API Key 环境变量"
          name="tron_api_key_env_var"
          :rules="[
            { required: true, message: '请输入 API Key 环境变量名' },
            {
              pattern: /^[A-Z][A-Z0-9_]{2,63}$/,
              message: '请输入大写环境变量名，例如 TRONGRID_API_KEY',
            },
          ]"
        >
          <Input
            v-model:value="form.tron_api_key_env_var"
            placeholder="TRONGRID_API_KEY"
          />
        </FormItem>
        <FormItem label="TRON API Key" name="tron_api_key">
          <Input.TextArea
            v-model:value="apiKeyInput"
            :auto-size="{ minRows: 3, maxRows: 6 }"
            placeholder="可选；多个 Key 请每行一个，或用逗号/分号分隔"
          />
          <div class="mt-2 text-sm text-gray-500">
            当前状态：{{ form.tron_api_key_preview || '未配置' }}
          </div>
        </FormItem>
        <FormItem label="API Key 状态">
          <Tag :color="form.tron_api_key_configured ? 'success' : 'warning'">
            {{ form.tron_api_key_configured ? '已配置' : '未配置' }}
          </Tag>
        </FormItem>
        <Alert
          class="mb-4"
          message="API Key 按当前部署要求以明文保存，页面只显示脱敏预览；数据库未配置时使用上方环境变量作为兜底。请妥善保护数据库及备份。"
          show-icon
          type="info"
        />
        <FormItem label="轮询间隔（秒）">
          <InputNumber
            v-model:value="form.tron_poll_interval"
            :disabled="!form.tron_monitor_enabled"
            :min="5"
            :max="3600"
            :step="5"
            style="width: 180px"
          />
        </FormItem>
        <FormItem :wrapper-col="{ offset: 5, span: 15 }">
          <Space>
            <Button html-type="submit" type="primary" :loading="saving"
              >保存设置</Button
            >
            <Button :disabled="saving" @click="loadSettings">重新加载</Button>
          </Space>
        </FormItem>
      </Card>
    </Form>
  </Page>
</template>
