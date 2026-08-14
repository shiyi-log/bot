<script lang="ts" setup>
import type { TablePaginationConfig } from 'ant-design-vue';

import type { DashboardUserItem } from '#/api/admin';

import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Table,
} from 'ant-design-vue';

import {
  deleteDashboardUserApi,
  getDashboardUsersApi,
  updateDashboardUserBalanceApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const keyword = ref('');
const items = ref<DashboardUserItem[]>([]);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  totalPages: 0,
});
const editOpen = ref(false);
const currentRow = ref<DashboardUserItem | null>(null);
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const formState = reactive({
  balance: '0',
  balance_trx: '0',
  cloud_discount_rate: '100.00',
});

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  {
    title: 'Telegram ID',
    dataIndex: 'tg_user_id',
    key: 'tg_user_id',
    width: 180,
  },
  {
    title: '展示名',
    dataIndex: 'display_name',
    key: 'display_name',
    width: 180,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 260,
  },
  { title: '代理数', dataIndex: 'proxy_count', key: 'proxy_count', width: 110 },
  {
    title: '折扣',
    dataIndex: 'cloud_discount_rate',
    key: 'cloud_discount_rate',
    width: 120,
  },
  { title: 'USDT 余额', dataIndex: 'balance', key: 'balance', width: 140 },
  {
    title: 'TRX 余额',
    dataIndex: 'balance_trx',
    key: 'balance_trx',
    width: 140,
  },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 220 },
  { title: '操作', key: 'actions', fixed: 'right' as const, width: 240 },
];

async function loadData() {
  loading.value = true;
  try {
    const response = await getDashboardUsersApi({
      keyword: keyword.value.trim(),
      page: pagination.current,
      page_size: pagination.pageSize,
    });
    items.value = response.items;
    pagination.current = response.page;
    pagination.pageSize = response.page_size;
    pagination.total = response.total;
    pagination.totalPages = response.total_pages;
  } finally {
    loading.value = false;
  }
}

function searchUsers() {
  pagination.current = 1;
  loadData();
}

function usernamePipeLabel(value?: null | string) {
  const raw = String(value || '').trim();
  if (!raw || raw === '-') return '-';
  return raw
    .split(/\s*[/|｜]\s*/)
    .map((item) => item.trim())
    .filter(Boolean)
    .join('｜');
}

function resetSearch() {
  keyword.value = '';
  pagination.current = 1;
  loadData();
}

function handleTableChange(nextPagination: TablePaginationConfig) {
  pagination.current = Number(nextPagination.current || 1);
  pagination.pageSize = Number(nextPagination.pageSize || 10);
  loadData();
}

function openEdit(record: DashboardUserItem) {
  if (!requireCloudDangerPermission('编辑用户余额和折扣')) return;
  currentRow.value = record;
  formState.balance = record.balance;
  formState.balance_trx = record.balance_trx;
  formState.cloud_discount_rate = record.cloud_discount_rate || '100.00';
  editOpen.value = true;
}

function openBalanceDetail(record: DashboardUserItem) {
  router.push(`/admin/users/${record.id}/balance-details`).catch(() => {});
}

async function submitEdit() {
  if (!currentRow.value) return;
  if (!requireCloudDangerPermission('保存用户余额和折扣')) return;
  saving.value = true;
  try {
    await updateDashboardUserBalanceApi(currentRow.value.id, {
      balance: formState.balance,
      balance_trx: formState.balance_trx,
      cloud_discount_rate: formState.cloud_discount_rate,
    });
    message.success('用户余额和折扣已更新');
    editOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '更新失败');
  } finally {
    saving.value = false;
  }
}

async function removeUser(record: DashboardUserItem) {
  if (!requireCloudDangerPermission('删除用户')) return;
  saving.value = true;
  try {
    await deleteDashboardUserApi(record.id);
    message.success('用户已删除，ID 已加入新用户复用队列');
    if (items.value.length <= 1 && pagination.current > 1) {
      pagination.current -= 1;
    }
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '删除失败');
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page
    description="读取 Django 用户数据，支持用户名、折扣与余额修改"
    title="用户列表"
  >
    <Card>
      <template #title>
        <Space>
          <span>用户数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索 TG ID、用户名、昵称"
            style="width: 320px"
            @search="searchUsers"
          />
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>
      <Table
        class="users-table"
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          pageSizeOptions: ['10', '20', '50', '100'],
          showLessItems: false,
          showQuickJumper: true,
          showSizeChanger: true,
          showTotal: (total: number) =>
            `共 ${total} 条 / ${pagination.totalPages} 页`,
          total: pagination.total,
        }"
        row-key="id"
        :scroll="{ x: 1580 }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'display_name'">
            <div class="font-medium">{{ record.display_name || '-' }}</div>
          </template>
          <template v-else-if="column.key === 'username_label'">
            <span>{{ usernamePipeLabel(record.username_label) }}</span>
          </template>
          <template v-else-if="column.key === 'proxy_count'">
            <span>{{ record.proxy_count || 0 }}</span>
          </template>
          <template v-else-if="column.key === 'cloud_discount_rate'">
            <span>{{ record.cloud_discount_rate || '100.00' }}%</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button
                type="link"
                @click="openBalanceDetail(record as DashboardUserItem)"
              >
                余额明细
              </Button>
              <Button
                type="link"
                :disabled="!canRunCloudDanger"
                @click="openEdit(record as DashboardUserItem)"
              >
                编辑
              </Button>
              <Popconfirm
                title="确认删除该用户信息吗？"
                description="仅允许删除无业务记录的用户；删除后资产/IP会解绑，新用户优先复用该ID。"
                @confirm="removeUser(record as DashboardUserItem)"
              >
                <Button danger type="link" :disabled="!canRunCloudDanger">
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
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      title="编辑余额/折扣"
      @ok="submitEdit"
    >
      <Form layout="vertical">
        <Form.Item label="用户">
          <Input :value="currentRow?.display_name || ''" disabled />
        </Form.Item>
        <Form.Item label="USDT 余额">
          <Input
            v-model:value="formState.balance"
            placeholder="请输入 USDT 余额"
          />
        </Form.Item>
        <Form.Item label="TRX 余额">
          <Input
            v-model:value="formState.balance_trx"
            placeholder="请输入 TRX 余额"
          />
        </Form.Item>
        <Form.Item label="折扣(%)">
          <Input
            v-model:value="formState.cloud_discount_rate"
            placeholder="请输入折扣，100 表示无折扣"
          />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.users-table :deep(.ant-table-cell) {
  vertical-align: middle;
}

.users-table :deep(.ant-table-cell:nth-child(1)),
.users-table :deep(.ant-table-cell:nth-child(2)),
.users-table :deep(.ant-table-cell:nth-child(7)),
.users-table :deep(.ant-table-cell:nth-child(8)),
.users-table :deep(.ant-table-cell:nth-child(9)) {
  white-space: nowrap;
}
</style>
