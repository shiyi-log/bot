<script lang="ts" setup>
import type { TableColumnsType, TablePaginationConfig } from 'ant-design-vue';

import type { TronAddress, TronAddressPayload } from '#/api/telegram';

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
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  createTronAddressApi,
  deleteTronAddressApi,
  getTronAddressesApi,
  updateTronAddressApi,
} from '#/api/telegram';

const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const editingId = ref<null | number>(null);
const keyword = ref('');
const items = ref<TronAddress[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
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
  { title: '余额', dataIndex: 'balance_sun', key: 'balance_sun', width: 140 },
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

const statusMeta = {
  error: { color: 'error', text: '异常' },
  ok: { color: 'success', text: '正常' },
  pending: { color: 'processing', text: '待检查' },
} as const;

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

onMounted(loadData);
</script>

<template>
  <Page
    description="维护需要轮询余额和交易状态的 TRON 地址"
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
