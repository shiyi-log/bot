<script lang="ts" setup>
import type {
  DashboardButtonConfig,
  DashboardButtonConfigItem,
} from '#/api/admin';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  message,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  getDashboardButtonConfigApi,
  initDashboardButtonConfigApi,
  updateDashboardButtonConfigApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const config = ref<DashboardButtonConfig>({ items: [], row_size: 2 });
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const columns = [
  { title: '类型', dataIndex: 'type', key: 'type', width: 110 },
  { title: '键盘文案', dataIndex: 'label', key: 'label', width: 180 },
  {
    title: '按钮文案',
    dataIndex: 'button_label',
    key: 'button_label',
    width: 180,
  },
  { title: '按钮链接', dataIndex: 'url', key: 'url', width: 240 },
  { title: '附带消息', dataIndex: 'message', key: 'message', width: 320 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 120 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'action', width: 100 },
];

function normalizeItems(items: DashboardButtonConfigItem[]) {
  return [...items].toSorted(
    (a, b) =>
      Number(a.sort_order || 0) - Number(b.sort_order || 0) ||
      a.key.localeCompare(b.key),
  );
}

async function loadData() {
  loading.value = true;
  try {
    const data = await getDashboardButtonConfigApi();
    config.value = { ...data, items: normalizeItems(data.items || []) };
  } catch (error: any) {
    message.error(error?.message || '加载按钮设置失败');
  } finally {
    loading.value = false;
  }
}

async function initConfig() {
  if (!requireCloudDangerPermission('初始化按钮配置')) return;
  loading.value = true;
  try {
    const data = await initDashboardButtonConfigApi();
    config.value = { ...data, items: normalizeItems(data.items || []) };
    message.success('已初始化按钮配置');
  } catch (error: any) {
    message.error(error?.message || '初始化失败');
  } finally {
    loading.value = false;
  }
}

function addLinkButton() {
  if (!requireCloudDangerPermission('添加自定义键盘')) return;
  config.value.items.push({
    enabled: true,
    key: `link_${Date.now()}`,
    button_label: '打开链接',
    label: '新链接按钮',
    locked: false,
    sort_order: 100,
    message: '请点击下面按钮打开链接',
    type: 'link',
    url: 'https://',
  });
}

function removeItem(record: Record<string, any>) {
  if (!requireCloudDangerPermission('删除自定义键盘')) return;
  config.value.items = config.value.items.filter(
    (item) => item.key !== record.key,
  );
}

async function saveConfig() {
  if (!requireCloudDangerPermission('保存按钮配置')) return;
  saving.value = true;
  try {
    const data = await updateDashboardButtonConfigApi({
      row_size: Number(config.value.row_size || 2),
      items: normalizeItems(config.value.items),
    });
    config.value = { ...data, items: normalizeItems(data.items || []) };
    message.success('按钮设置已保存');
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page
    description="设置机器人底部键盘、自定义链接按钮、附带消息和跳转链接"
    title="按钮设置"
  >
    <Card :loading="loading">
      <Form layout="vertical">
        <Form.Item label="每排显示数量">
          <InputNumber v-model:value="config.row_size" :max="4" :min="1" />
        </Form.Item>
      </Form>

      <Space class="mb-3">
        <Button
          type="primary"
          :disabled="!canRunCloudDanger"
          :loading="saving"
          @click="saveConfig"
        >
          保存设置
        </Button>
        <Button :disabled="!canRunCloudDanger" @click="addLinkButton">
          添加自定义键盘
        </Button>
        <Button :loading="loading" @click="loadData">刷新</Button>
        <Button
          :disabled="!canRunCloudDanger"
          :loading="loading"
          @click="initConfig"
        >
          初始化默认按钮
        </Button>
      </Space>

      <Table
        :columns="columns"
        :data-source="config.items"
        :pagination="false"
        row-key="key"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <Tag :color="record.type === 'business' ? 'blue' : 'green'">
              {{ record.type === 'business' ? '业务按钮' : '自定义键盘' }}
            </Tag>
          </template>

          <template v-else-if="column.key === 'label'">
            <span v-if="record.locked">{{ record.label }}</span>
            <Input v-else v-model:value="record.label" />
          </template>

          <template v-else-if="column.key === 'button_label'">
            <span v-if="record.type === 'business'" class="text-gray-400">-</span>
            <Input
              v-else
              v-model:value="record.button_label"
              placeholder="例如：立即打开"
            />
          </template>

          <template v-else-if="column.key === 'url'">
            <span v-if="record.type === 'business'" class="text-gray-400">业务按钮不支持链接编辑</span>
            <Input
              v-else
              v-model:value="record.url"
              placeholder="https://example.com 或 @shiyi4"
            />
          </template>

          <template v-else-if="column.key === 'message'">
            <span v-if="record.type === 'business'" class="text-gray-400">-</span>
            <Input.TextArea
              v-else
              v-model:value="record.message"
              :auto-size="{ minRows: 1, maxRows: 3 }"
              placeholder="点击键盘后发送给用户的消息"
            />
          </template>

          <template v-else-if="column.key === 'sort_order'">
            <InputNumber v-model:value="record.sort_order" :min="0" />
          </template>

          <template v-else-if="column.key === 'enabled'">
            <Switch
              v-model:checked="record.enabled"
              :disabled="record.locked || !canRunCloudDanger"
            />
          </template>

          <template v-else-if="column.key === 'action'">
            <Popconfirm
              v-if="!record.locked"
              title="确认删除这个链接按钮？"
              @confirm="removeItem(record)"
            >
              <Button danger size="small" :disabled="!canRunCloudDanger">
                删除
              </Button>
            </Popconfirm>
            <span v-else class="text-gray-400">仅排序</span>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
