<script lang="ts" setup>
import type { BotSettings, BotSettingsUpdate } from '#/api/telegram';

import { onMounted, reactive, ref } from 'vue';

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

const loading = ref(false);
const saving = ref(false);
const apiKeyDirty = ref(false);
const form = reactive<BotSettings>({
  tron_api_key_configured: false,
  tron_api_key_env_var: 'TRONGRID_API_KEY',
  tron_api_key_preview: '',
  tron_api_key: '',
  tron_api_url: 'https://api.trongrid.io',
  tron_monitor_enabled: false,
  tron_poll_interval: 30,
  updated_at: null,
});

async function loadSettings() {
  loading.value = true;
  try {
    Object.assign(form, await getBotSettingsApi());
    form.tron_api_key = '';
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
    Object.assign(form, await updateBotSettingsApi(payload));
    form.tron_api_key = '';
    apiKeyDirty.value = false;
    message.success('设置已保存');
  } finally {
    saving.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <Page description="配置 TRON 只读监控的运行参数" title="运行设置">
    <Card :loading="loading" class="max-w-4xl" title="TRON 监控">
      <Form
        :label-col="{ span: 5 }"
        :wrapper-col="{ span: 15 }"
        @finish="saveSettings"
      >
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
          <Input v-model:value="form.tron_api_url" placeholder="https://api.trongrid.io" />
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
          <Input v-model:value="form.tron_api_key_env_var" placeholder="TRONGRID_API_KEY" />
        </FormItem>
        <FormItem label="TRON API Key" name="tron_api_key">
          <Input.TextArea
            v-model:value="form.tron_api_key"
            :auto-size="{ minRows: 3, maxRows: 6 }"
            placeholder="可选；多个 Key 请每行一个，或用逗号/分号分隔"
            @update:value="apiKeyDirty = true"
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
          message="这里只保存 API 地址和环境变量名。API Key 必须在 Django 服务端环境中配置，不会通过页面提交。"
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
      </Form>
    </Card>
  </Page>
</template>
