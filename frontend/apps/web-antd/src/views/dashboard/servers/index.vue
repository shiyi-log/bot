<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { DashboardServerItem } from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  message,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getDashboardServersPageApi,
  syncDashboardServersApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const syncing = ref(false);
const keyword = ref('');
const totalSortMode = ref<
  | 'default'
  | 'expires_asc'
  | 'expires_desc'
  | 'remaining_asc'
  | 'remaining_desc'
>('default');
const items = ref<DashboardServerItem[]>([]);
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
});
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const columns = computed<TableColumnsType<DashboardServerItem>>(() => [
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 220,
  },
  {
    title: '服务器名',
    dataIndex: 'server_name',
    key: 'server_name',
    width: 220,
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 140 },
  {
    title: '账号ID',
    dataIndex: 'account_label',
    key: 'account_label',
    width: 160,
  },
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 160 },
  { title: '公网 IP', dataIndex: 'public_ip', key: 'public_ip', width: 150 },
  { title: '关联订单', dataIndex: 'order_no', key: 'order_no', width: 220 },
  {
    title: '剩余天数',
    dataIndex: 'status_countdown',
    key: 'status_countdown',
    sorter: true,
    sortOrder:
      totalSortMode.value === 'remaining_asc'
        ? 'ascend'
        : (totalSortMode.value === 'remaining_desc'
          ? 'descend'
          : undefined),
    width: 160,
  },
  {
    title: '到期时间',
    dataIndex: 'expires_at',
    key: 'expires_at',
    sorter: true,
    sortOrder:
      totalSortMode.value === 'expires_asc'
        ? 'ascend'
        : (totalSortMode.value === 'expires_desc'
          ? 'descend'
          : undefined),
    width: 200,
  },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 200 },
]);

function totalSortParams() {
  if (totalSortMode.value === 'expires_asc') {
    return { sort_by: 'expires_at' as const, sort_order: 'asc' as const };
  }
  if (totalSortMode.value === 'expires_desc') {
    return { sort_by: 'expires_at' as const, sort_order: 'desc' as const };
  }
  if (totalSortMode.value === 'remaining_asc') {
    return { sort_by: 'days_left' as const, sort_order: 'asc' as const };
  }
  if (totalSortMode.value === 'remaining_desc') {
    return { sort_by: 'days_left' as const, sort_order: 'desc' as const };
  }
  return {};
}

function handleServerTableChange(
  tablePagination: any,
  _filters: unknown,
  sorter: any,
) {
  const nextPage = Number(tablePagination?.current || pagination.current || 1);
  const nextPageSize = Number(
    tablePagination?.pageSize || pagination.pageSize || 50,
  );
  const activeSorter = Array.isArray(sorter)
    ? sorter.find((item) => item.order)
    : sorter;
  const key = activeSorter?.columnKey || activeSorter?.field;
  const order = activeSorter?.order;
  if (!['expires_at', 'status_countdown'].includes(key)) {
    pagination.current = nextPage;
    pagination.pageSize = nextPageSize;
    loadData();
    return;
  }
  if (!order) {
    totalSortMode.value = 'default';
  } else if (key === 'expires_at') {
    totalSortMode.value = order === 'ascend' ? 'expires_asc' : 'expires_desc';
  } else if (key === 'status_countdown') {
    totalSortMode.value =
      order === 'ascend' ? 'remaining_asc' : 'remaining_desc';
  }
  pagination.current = nextPage;
  pagination.pageSize = nextPageSize;
  loadData();
}

async function loadData() {
  loading.value = true;
  try {
    const response = await getDashboardServersPageApi({
      dedup: 0,
      keyword: keyword.value.trim(),
      page: pagination.current,
      page_size: pagination.pageSize,
      ...totalSortParams(),
    });
    items.value = response.items || [];
    pagination.current = response.page || pagination.current;
    pagination.pageSize = response.page_size || pagination.pageSize;
    pagination.total = response.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetSearch() {
  keyword.value = '';
  pagination.current = 1;
  loadData();
}

async function syncServers() {
  if (!requireCloudDangerPermission('同步服务器')) return;
  syncing.value = true;
  try {
    await syncDashboardServersApi();
    message.success('服务器同步完成');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '服务器同步失败');
  } finally {
    syncing.value = false;
  }
}

function goToCloudOrder(orderId: null | number, orderDetailPath?: string) {
  if (!orderId || !orderDetailPath) {
    return;
  }
  router.push(orderDetailPath).catch(() => {});
}

function formatTimeLeft(expiresAt: null | string) {
  if (!expiresAt) {
    return '-';
  }

  const expireTime = dayjs(expiresAt);
  if (!expireTime.isValid()) {
    return '-';
  }

  const now = dayjs();
  const diffMinutes = expireTime.diff(now, 'minute');

  if (diffMinutes < 0) {
    return '已到期';
  }
  if (diffMinutes < 60) {
    return diffMinutes === 0 ? '0 天' : `剩余 ${diffMinutes} 分钟`;
  }

  const diffHours = expireTime.diff(now, 'hour');
  if (diffHours < 24) {
    return `剩余 ${diffHours} 小时`;
  }

  const diffDays = expireTime.diff(now, 'day');
  return `剩余 ${Math.max(diffDays, 0)} 天`;
}

onMounted(loadData);
</script>

<template>
  <Page description="从真实服务器 API 查看同步后的服务器记录" title="服务器表">
    <Card>
      <template #title>
        <Space>
          <span>服务器数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索服务器名、实例 ID、资源 ID、IP、订单号"
            style="width: 380px"
            @search="
              () => {
                pagination.current = 1;
                loadData();
              }
            "
          />
          <Button
            size="small"
            :disabled="!canRunCloudDanger"
            :loading="syncing"
            @click="syncServers"
          >
            同步服务器
          </Button>
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>
      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          total: pagination.total,
          showTotal: (total) => `共 ${total} 条`,
        }"
        row-key="id"
        :scroll="{ x: 2100 }"
        @change="handleServerTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username_label'">
            <span>{{ record.username_label || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'server_name'">
            <div>{{ record.server_name || '-' }}</div>
            <div class="text-xs text-gray-400">
              {{ record.instance_id || '-' }}
            </div>
          </template>
          <template v-else-if="column.key === 'order_no'">
            <Button
              v-if="record.order_id && record.order_detail_path"
              type="link"
              size="small"
              @click="goToCloudOrder(record.order_id, record.order_detail_path)"
            >
              {{ record.order_no }}
            </Button>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <div>
              <Tag
                :color="
                  record.is_active
                    ? 'success'
                    : record.status === 'deleted' ||
                        record.status === 'terminated'
                      ? 'default'
                      : 'warning'
                "
              >
                {{ record.status_label || record.status || '-' }}
              </Tag>
            </div>
            <div class="text-xs text-gray-400">
              {{ record.status_countdown || record.provider_status || '-' }}
            </div>
          </template>
          <template v-else-if="column.key === 'status_countdown'">
            <span>{{
              record.status_countdown || formatTimeLeft(record.expires_at)
            }}</span>
          </template>
          <template v-else-if="column.key === 'expires_at'">
            <div>
              {{
                record.expires_at
                  ? dayjs(record.expires_at).format('YYYY-MM-DD HH:mm')
                  : '待人工添加'
              }}
            </div>
            <div class="text-xs text-gray-400">
              {{ formatTimeLeft(record.expires_at) }}
            </div>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
