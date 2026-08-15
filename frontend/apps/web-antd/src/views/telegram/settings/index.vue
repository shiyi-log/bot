<script lang="ts" setup>
import type { BotSettings, BotSettingsUpdate } from '#/api/telegram';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  FormItem,
  InputNumber,
  Space,
  Switch,
  message,
} from 'ant-design-vue';

import { getBotSettingsApi, updateBotSettingsApi } from '#/api/telegram';

const loading = ref(false);
const saving = ref(false);
const form = reactive<BotSettings>({
  tron_monitor_enabled: false,
  tron_poll_interval: 30,
  updated_at: null,
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
      tron_monitor_enabled: form.tron_monitor_enabled,
      tron_poll_interval: form.tron_poll_interval,
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
