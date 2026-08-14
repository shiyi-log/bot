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
  message,
} from 'ant-design-vue';

import { getBotSettingsApi, updateBotSettingsApi } from '#/api/telegram';

const loading = ref(false);
const saving = ref(false);
const form = reactive<BotSettings>({
  bot_enabled: false,
  tron_monitor_enabled: false,
  tron_poll_interval: 30,
  updated_at: null,
  welcome_enabled: true,
  welcome_message: '',
});

async function loadSettings() {
  loading.value = true;
  try {
    Object.assign(form, await getBotSettingsApi());
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  saving.value = true;
  try {
    const payload: BotSettingsUpdate = {
      bot_enabled: form.bot_enabled,
      tron_monitor_enabled: form.tron_monitor_enabled,
      tron_poll_interval: form.tron_poll_interval,
      welcome_enabled: form.welcome_enabled,
      welcome_message: form.welcome_message,
    };
    Object.assign(form, await updateBotSettingsApi(payload));
    message.success('设置已保存');
  } finally {
    saving.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <Page
    description="配置欢迎消息、机器人开关与 TRON 监控参数"
    title="机器人设置"
  >
    <Card :loading="loading" class="max-w-4xl" title="基础配置">
      <Form
        :label-col="{ span: 5 }"
        :wrapper-col="{ span: 15 }"
        @finish="saveSettings"
      >
        <FormItem label="运行机器人">
          <Switch v-model:checked="form.bot_enabled" />
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
            :disabled="!form.welcome_enabled"
            :auto-size="{ minRows: 4, maxRows: 10 }"
            placeholder="欢迎 {first_name} 加入 {group_title}！"
            show-count
            :maxlength="2000"
          />
          <Alert
            class="mt-3"
            message="可用变量：{first_name}、{last_name}、{username}、{group_title}"
            show-icon
            type="info"
          />
        </FormItem>
        <FormItem label="启用 TRON 监控">
          <Switch v-model:checked="form.tron_monitor_enabled" />
        </FormItem>
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
