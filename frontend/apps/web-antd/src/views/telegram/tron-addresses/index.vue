<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type {
  TronAddress,
  TronAddressPayload,
  TronAlert,
  TronAlertType,
} from '#/api/telegram';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  FormItem,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  createTronAddressApi,
  checkTronAddressApi,
  deleteTronAddressApi,
  getTronAddressesApi,
  getTronAlertsApi,
  updateTronAddressApi,
} from '#/api/telegram';

const loading = ref(false);
const saving = ref(false);
const checkingId = ref<null | number>(null);
const modalOpen = ref(false);
const editingId = ref<null | number>(null);
const keyword = ref('');
const items = ref<TronAddress[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
const alertLoading = ref(false);
const alertKeyword = ref('');
const alertType = ref<TronAlertType | undefined>();
const alerts = ref<TronAlert[]>([]);
const alertPagination = reactive({ page: 1, pageSize: 20, total: 0 });
const form = reactive<TronAddressPayload>({
  address: '',
  enabled: true,
  label: '',
});

const modalTitle = computed(() =>
  editingId.value ? '编辑监控地址' : '新增监控地址',
);
const columns: TableColumnsType<TronAddress> = [
  {
    title: '地址',
    dataIndex: 'address',
    key: 'address',
    fixed: 'left',
    width: 360,
  },
  { title: '备注', dataIndex: 'label', key: 'label', width: 180 },
  { title: 'TRX 余额', dataIndex: 'balance_sun', key: 'balance_sun', width: 140 },
  { title: 'USDT 余额', dataIndex: 'usdt_balance_sun', key: 'usdt_balance_sun', width: 140 },
  { title: '监控状态', dataIndex: 'enabled', key: 'enabled', width: 110 },
  { title: '检查结果', dataIndex: 'status', key: 'status', width: 120 },
  {
    title: '最近检查',
    dataIndex: 'last_checked_at',
    key: 'last_checked_at',
    width: 180,
  },
  { title: '错误信息', dataIndex: 'last_error', key: 'last_error', width: 240 },
  { title: '操作', key: 'actions', fixed: 'right', width: 150 },
];
const alertColumns: TableColumnsType<TronAlert> = [
  { title: '提醒类型', dataIndex: 'alert_type', key: 'alert_type', width: 140 },
  { title: '监控地址', dataIndex: 'address_value', key: 'address_value', width: 350 },
  { title: '备注', dataIndex: 'address_label', key: 'address_label', width: 160 },
  { title: '区块', dataIndex: 'block_number', key: 'block_number', width: 120 },
  { title: '区块时间', dataIndex: 'block_timestamp', key: 'block_timestamp', width: 180 },
  { title: '交易 ID', dataIndex: 'tx_id', key: 'tx_id', width: 260 },
  { title: '变更前', dataIndex: 'previous_value', key: 'previous_value', width: 300 },
  { title: '变更后', dataIndex: 'current_value', key: 'current_value', width: 300 },
  { title: '发现时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
];

const statusMeta = {
  error: { color: 'error', text: '异常' },
  ok: { color: 'success', text: '正常' },
  pending: { color: 'processing', text: '待检查' },
} as const;
const alertTypeMeta = {
  authorization_changed: { color: 'warning', text: '授权变动' },
  permission_changed: { color: 'error', text: '权限变动' },
  resource_changed: { color: 'processing', text: '资源变动' },
} as const;
const alertTypeOptions = Object.entries(alertTypeMeta).map(([value, meta]) => ({
  label: meta.text,
  value,
}));

async function loadData() {
  loading.value = true;
  try {
    const result = await getTronAddressesApi({
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

async function loadAlerts() {
  alertLoading.value = true;
  try {
    const result = await getTronAlertsApi({
      alert_type: alertType.value,
      ordering: '-created_at',
      page: alertPagination.page,
      page_size: alertPagination.pageSize,
      search: alertKeyword.value.trim(),
    });
    alerts.value = result.results;
    alertPagination.total = result.count;
  } finally {
    alertLoading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, { address: '', enabled: true, label: '' });
  modalOpen.value = true;
}

function openEdit(record: Record<string, any>) {
  editingId.value = record.id;
  Object.assign(form, {
    address: record.address,
    enabled: record.enabled,
    label: record.label,
  });
  modalOpen.value = true;
}

async function saveAddress() {
  saving.value = true;
  try {
    const payload = {
      ...form,
      address: form.address.trim(),
      label: form.label.trim(),
    };
    if (editingId.value) {
      await updateTronAddressApi(editingId.value, payload);
    } else {
      await createTronAddressApi(payload);
    }
    message.success(editingId.value ? '监控地址已更新' : '监控地址已添加');
    modalOpen.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function removeAddress(id: number) {
  await deleteTronAddressApi(id);
  message.success('监控地址已删除');
  if (items.value.length === 1 && pagination.page > 1) pagination.page -= 1;
  await loadData();
}

async function checkAddress(id: number) {
  checkingId.value = id;
  try {
    await checkTronAddressApi(id);
    message.success('地址检查完成');
    await loadData();
  } finally {
    checkingId.value = null;
  }
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

function searchAlerts() {
  alertPagination.page = 1;
  loadAlerts();
}

function resetAlertSearch() {
  alertKeyword.value = '';
  alertType.value = undefined;
  alertPagination.page = 1;
  loadAlerts();
}

function handleAlertTableChange(next: TablePaginationConfig) {
  alertPagination.page = next.current || 1;
  alertPagination.pageSize = next.pageSize || 20;
  loadAlerts();
}

function formatDate(value: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function getStatusMeta(status: string) {
  return (
    statusMeta[status as keyof typeof statusMeta] || {
      color: 'default',
      text: status,
    }
  );
}

function getAlertTypeMeta(type: string) {
  return (
    alertTypeMeta[type as keyof typeof alertTypeMeta] || {
      color: 'default',
      text: type,
    }
  );
}

function formatSnapshot(value: Record<string, unknown>) {
  const entries = Object.entries(value || {});
  if (!entries.length) return '-';
  return entries
    .map(([key, item]) => {
      const formatted =
        item && typeof item === 'object' ? JSON.stringify(item) : String(item);
      return `${key}: ${formatted}`;
    })
    .join('\n');
}

onMounted(() => {
  loadData();
  loadAlerts();
});
</script>

<template>
  <Page
    description="维护只读监控地址，并查看资源、授权和账户权限变动"
    title="TRON 地址监控"
  >
    <Card>
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>监控地址</span>
          <Space wrap>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索地址或备注"
              style="width: 320px"
              @search="search"
            />
            <Button @click="resetSearch">重置</Button>
            <Button @click="loadData">刷新</Button>
            <Button type="primary" @click="openCreate">新增地址</Button>
          </Space>
        </div>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }"
        row-key="id"
        :scroll="{ x: 1500 }"
        sticky
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'balance_sun'">
            {{ (Number(record.balance_sun || 0) / 1_000_000).toLocaleString() }}
            TRX
          </template>
          <template v-else-if="column.key === 'usdt_balance_sun'">
            {{ (Number(record.usdt_balance_sun || 0) / 1_000_000).toLocaleString() }}
            USDT
          </template>
          <template v-else-if="column.key === 'enabled'">
            <Tag :color="record.enabled ? 'success' : 'default'">
              {{ record.enabled ? '已启用' : '已停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="getStatusMeta(record.status).color">
              {{ getStatusMeta(record.status).text }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'last_checked_at'">
            {{ formatDate(record.last_checked_at) }}
          </template>
          <template v-else-if="column.key === 'last_error'">
            <span class="break-all text-red-500">{{
              record.last_error || '-'
            }}</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button :loading="checkingId === record.id" size="small" type="link" @click="checkAddress(record.id)">检查</Button>
              <Button size="small" type="link" @click="openEdit(record)"
                >编辑</Button
              >
              <Popconfirm
                title="确认删除这个监控地址？"
                @confirm="removeAddress(record.id)"
              >
                <Button danger size="small" type="link">删除</Button>
              </Popconfirm>
            </Space>
          </template>
        </template>
      </Table>
    </Card>

    <Card class="mt-4">
      <template #title>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>变动提醒</span>
          <Space wrap>
            <Select
              v-model:value="alertType"
              allow-clear
              :options="alertTypeOptions"
              placeholder="全部提醒类型"
              style="width: 160px"
              @change="searchAlerts"
            />
            <Input.Search
              v-model:value="alertKeyword"
              allow-clear
              enter-button="搜索"
              placeholder="搜索地址、备注或交易 ID"
              style="width: 320px"
              @search="searchAlerts"
            />
            <Button @click="resetAlertSearch">重置</Button>
            <Button @click="loadAlerts">刷新</Button>
          </Space>
        </div>
      </template>
      <Table
        :columns="alertColumns"
        :data-source="alerts"
        :loading="alertLoading"
        :pagination="{
          current: alertPagination.page,
          pageSize: alertPagination.pageSize,
          total: alertPagination.total,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }"
        row-key="id"
        :scroll="{ x: 1990 }"
        @change="handleAlertTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'alert_type'">
            <Tag :color="getAlertTypeMeta(record.alert_type).color">
              {{ getAlertTypeMeta(record.alert_type).text }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'address_value'">
            <span class="font-mono">{{ record.address_value }}</span>
          </template>
          <template v-else-if="column.key === 'block_number'">
            {{ record.block_number ?? '-' }}
          </template>
          <template v-else-if="column.key === 'block_timestamp'">
            {{ formatDate(record.block_timestamp) }}
          </template>
          <template v-else-if="column.key === 'tx_id'">
            <span class="break-all font-mono">{{ record.tx_id || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'previous_value'">
            <pre class="snapshot-cell">{{ formatSnapshot(record.previous_value) }}</pre>
          </template>
          <template v-else-if="column.key === 'current_value'">
            <pre class="snapshot-cell">{{ formatSnapshot(record.current_value) }}</pre>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="modalOpen"
      :confirm-loading="saving"
      :title="modalTitle"
      ok-text="保存"
      @ok="saveAddress"
    >
      <Form layout="vertical">
        <FormItem label="TRON 地址" required>
          <Input
            v-model:value="form.address"
            :disabled="Boolean(editingId)"
            placeholder="请输入以 T 开头的 Base58Check 地址"
          />
        </FormItem>
        <FormItem label="备注">
          <Input
            v-model:value="form.label"
            allow-clear
            placeholder="例如：项目收款地址"
          />
        </FormItem>
        <FormItem label="启用监控">
          <Switch v-model:checked="form.enabled" />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.snapshot-cell {
  max-height: 8rem;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
