<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { DashboardCloudOrderItem } from '#/api/admin';

import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  deleteDashboardCloudOrderApi,
  getDashboardCloudOrdersApi,
  updateDashboardCloudOrderApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const keyword = ref('');
const items = ref<DashboardCloudOrderItem[]>([]);
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const editOpen = ref(false);
const editSaving = ref(false);
const currentRow = ref<DashboardCloudOrderItem | null>(null);
const editForm = reactive({
  delete_at: null as any,
  pay_amount: '',
  provision_note: '',
  public_ip: '',
  server_name: '',
  actual_expires_at: null as any,
  status: '',
  suspend_at: null as any,
  total_amount: '',
  user_query: '',
});

const statusOptions = [
  { label: '待支付', value: 'pending' },
  { label: '已支付', value: 'paid' },
  { label: '开通中', value: 'provisioning' },
  { label: '已完成', value: 'completed' },
  { label: '续费待处理', value: 'renew_pending' },
  { label: '即将到期', value: 'expiring' },
  { label: '已关机', value: 'suspended' },
  { label: '删除中', value: 'deleting' },
  { label: '已删除', value: 'deleted' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
  { label: '已过期', value: 'expired' },
];

const columns: TableColumnsType<DashboardCloudOrderItem> = [
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 220 },
  { title: '厂商', dataIndex: 'provider', key: 'provider', width: 140 },
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 160 },
  { title: '套餐', dataIndex: 'plan_name', key: 'plan_name', width: 220 },
  {
    title: '来源',
    dataIndex: 'order_source_label',
    key: 'order_source',
    width: 180,
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  {
    title: '执行情况',
    dataIndex: 'execution_status',
    key: 'execution_status',
    width: 180,
  },
  { title: '公网 IP', dataIndex: 'public_ip', key: 'public_ip', width: 160 },
  { title: '金额', dataIndex: 'total_amount', key: 'total_amount', width: 180 },
  {
    title: '备注',
    dataIndex: 'provision_note',
    key: 'provision_note',
    width: 320,
  },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 220 },
  {
    title: '操作',
    dataIndex: 'action',
    key: 'action',
    fixed: 'right' as const,
    width: 150,
  },
];

function statusColor(status: string) {
  if (['completed', 'paid'].includes(status)) return 'green';
  if (['expiring', 'pending', 'provisioning', 'renew_pending'].includes(status))
    return 'orange';
  if (['cancelled', 'deleted', 'expired', 'failed'].includes(status))
    return 'red';
  return 'blue';
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    cancelled: '已取消',
    completed: '已完成',
    deleted: '已删除',
    expired: '已过期',
    expiring: '即将到期',
    failed: '失败',
    paid: '已支付',
    pending: '待处理',
    provisioning: '开通中',
    renew_pending: '续费待处理',
    suspended: '已关机',
    deleting: '删除中',
  };
  return labels[status] || status || '-';
}

function executionStatusColor(status?: string) {
  if (!status) return 'default';
  if (status.includes('failed')) return 'red';
  return 'blue';
}

function amountText(record: DashboardCloudOrderItem) {
  const currency = record.currency || 'USDT';
  const totalText = `${record.total_amount || '0'} ${currency}`;
  if (record.pay_amount) {
    return `总额 ${totalText} / 应付 ${record.pay_amount} ${currency}`;
  }
  return `总额 ${totalText}`;
}

function noteText(record: DashboardCloudOrderItem) {
  return (record.provision_note || '').trim() || '-';
}

function sourceTagColor(source?: string) {
  if (source === 'manual_owner_change') return 'purple';
  if (source === 'manual_expiry_change') return 'gold';
  if (source === 'manual_price_change') return 'cyan';
  if (source === 'manual_owner_expiry_change') return 'magenta';
  if (source === 'renewal' || source === 'renewal_rebuild') return 'blue';
  return 'default';
}

function orderSourceItems(record: DashboardCloudOrderItem) {
  const tagKeys = record.order_source_tags || [];
  const tagLabels = record.order_source_tag_labels || [];
  if (tagLabels.length > 0) {
    return tagLabels.map((label, index) => ({
      key: tagKeys[index] || record.order_source || label,
      label,
    }));
  }
  return record.order_source_label
    ? [
        {
          key: record.order_source || record.order_source_label,
          label: record.order_source_label,
        },
      ]
    : [];
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardCloudOrdersApi({
      keyword: keyword.value.trim(),
    });
  } finally {
    loading.value = false;
  }
}

function resetSearch() {
  keyword.value = '';
  loadData();
}

onMounted(loadData);

function goToDetail(orderId: number) {
  router.push(`/admin/cloud-orders/${orderId}`).catch(() => {});
}

function openEdit(record: DashboardCloudOrderItem) {
  if (!requireCloudDangerPermission('编辑云订单')) return;
  currentRow.value = record;
  editForm.user_query =
    record.username_label && record.username_label !== '-'
      ? record.username_label
      : '';
  editForm.server_name = (record as any).server_name || '';
  editForm.public_ip = record.public_ip || '';
  editForm.total_amount = record.total_amount || '';
  editForm.pay_amount = record.pay_amount || '';
  editForm.status = record.status || '';
  editForm.actual_expires_at = (record as any).actual_expires_at
    ? dayjs((record as any).actual_expires_at)
    : null;
  editForm.suspend_at = (record as any).suspend_at
    ? dayjs((record as any).suspend_at)
    : null;
  editForm.delete_at = (record as any).delete_at
    ? dayjs((record as any).delete_at)
    : null;
  editForm.provision_note = record.provision_note || '';
  editOpen.value = true;
}

async function saveEdit() {
  if (!requireCloudDangerPermission('保存云订单')) return;
  if (!currentRow.value || editSaving.value) return;
  editSaving.value = true;
  try {
    await updateDashboardCloudOrderApi(currentRow.value.id, {
      delete_at: editForm.delete_at ? editForm.delete_at.toISOString() : null,
      pay_amount: editForm.pay_amount || null,
      provision_note: editForm.provision_note || null,
      public_ip: editForm.public_ip || null,
      server_name: editForm.server_name || null,
      actual_expires_at: editForm.actual_expires_at
        ? editForm.actual_expires_at.toISOString()
        : null,
      status: editForm.status,
      suspend_at: editForm.suspend_at
        ? editForm.suspend_at.toISOString()
        : null,
      total_amount: editForm.total_amount || null,
      user_query: editForm.user_query || null,
    });
    message.success('订单已保存');
    editOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存订单失败');
  } finally {
    editSaving.value = false;
  }
}

async function deleteOrder(record: DashboardCloudOrderItem) {
  if (!requireCloudDangerPermission('删除云订单')) return;
  await deleteDashboardCloudOrderApi(record.id);
  message.success('订单记录已删除');
  await loadData();
}
</script>

<template>
  <Page description="读取 Django 订单数据" title="订单列表">
    <Card>
      <template #title>
        <Space>
          <span>订单数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索订单号、厂商、地区、套餐、IP"
            style="width: 360px"
            @search="loadData"
          />
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
          <Button
            size="small"
            type="primary"
            @click="router.push('/admin/tasks/auto-renew')"
          >
            续费列表
          </Button>
        </Space>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        row-key="id"
        :scroll="{ x: 1900 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'order_no'">
            <a @click="goToDetail(Number(record.id))">{{ record.order_no }}</a>
          </template>
          <template v-else-if="column.key === 'order_source'">
            <Space :size="4" wrap>
              <Tag
                v-for="tag in orderSourceItems(
                  record as DashboardCloudOrderItem,
                )"
                :key="tag.key"
                :color="sourceTagColor(tag.key)"
              >
                {{ tag.label }}
              </Tag>
              <span
                v-if="
                  orderSourceItems(record as DashboardCloudOrderItem).length ===
                  0
                "
                >-</span>
            </Space>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="statusColor(record.status)">
              {{ record.status_label || statusLabel(record.status) }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'execution_status'">
            <Tag
              v-if="record.execution_status_label"
              :color="executionStatusColor(record.execution_status)"
            >
              {{ record.execution_status_label }}
            </Tag>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'total_amount'">
            {{ amountText(record as DashboardCloudOrderItem) }}
          </template>
          <template v-else-if="column.key === 'provision_note'">
            <span
              class="order-note"
              :title="noteText(record as DashboardCloudOrderItem)"
            >
              {{ noteText(record as DashboardCloudOrderItem) }}
            </span>
          </template>
          <template v-else-if="column.key === 'action'">
            <Space>
              <Button
                size="small"
                type="link"
                @click="goToDetail(Number(record.id))"
              >
                详情
              </Button>
              <Button
                size="small"
                type="link"
                :disabled="!canRunCloudDanger"
                @click="openEdit(record as DashboardCloudOrderItem)"
              >
                编辑
              </Button>
              <Popconfirm
                title="只删除后台订单记录，不删除真实云服务器或代理记录。确认删除？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="deleteOrder(record as DashboardCloudOrderItem)"
              >
                <Button
                  danger
                  size="small"
                  type="link"
                  :disabled="!canRunCloudDanger"
                >
                  删除
                </Button>
              </Popconfirm>
            </Space>
          </template>
        </template>
      </Table>
    </Card>
    <Modal
      v-model:open="editOpen"
      :confirm-loading="editSaving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      title="编辑订单"
      width="760px"
      @ok="saveEdit"
    >
      <Form layout="vertical">
        <Form.Item label="用户">
          <Input
            v-model:value="editForm.user_query"
            placeholder="支持 @username / t.me 链接 / Telegram ID"
          />
        </Form.Item>
        <Form.Item label="状态">
          <Select v-model:value="editForm.status" :options="statusOptions" />
        </Form.Item>
        <Form.Item label="服务器名">
          <Input v-model:value="editForm.server_name" />
        </Form.Item>
        <Form.Item label="公网 IP">
          <Input v-model:value="editForm.public_ip" />
        </Form.Item>
        <Form.Item label="总金额">
          <Input v-model:value="editForm.total_amount" />
        </Form.Item>
        <Form.Item label="应付金额">
          <Input v-model:value="editForm.pay_amount" />
        </Form.Item>
        <Form.Item label="服务到期时间">
          <DatePicker
            v-model:value="editForm.actual_expires_at"
            show-time
            class="w-full"
          />
        </Form.Item>
        <Form.Item label="计划关机时间">
          <DatePicker
            v-model:value="editForm.suspend_at"
            show-time
            class="w-full"
          />
        </Form.Item>
        <Form.Item label="计划删机时间">
          <DatePicker
            v-model:value="editForm.delete_at"
            show-time
            class="w-full"
          />
        </Form.Item>
        <Form.Item label="备注">
          <Input.TextArea v-model:value="editForm.provision_note" :rows="4" />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.order-note {
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
