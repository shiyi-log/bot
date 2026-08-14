<script lang="ts" setup>
import type { DashboardRechargeDetail } from '#/api/admin';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  Empty,
  message,
  Select,
  Space,
  Tag,
  Typography,
} from 'ant-design-vue';

import {
  getDashboardRechargeDetailApi,
  updateDashboardRechargeStatusApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const route = useRoute();
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const saving = ref(false);
const detail = ref<DashboardRechargeDetail | null>(null);
const selectedStatus = ref<string>('');

const rechargeId = computed(() => Number(route.params.id || 0));
const statusOptions = [
  { label: '待支付', value: 'pending' },
  { label: '已完成', value: 'completed' },
  { label: '已过期', value: 'expired' },
];

function statusColor(status?: string) {
  if (['completed'].includes(status || '')) return 'green';
  if (['pending'].includes(status || '')) return 'orange';
  if (['cancelled', 'expired', 'failed'].includes(status || '')) return 'red';
  return 'blue';
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    cancelled: '已取消',
    completed: '已完成',
    expired: '已过期',
    failed: '失败',
    pending: '待确认',
  };
  return detail.value?.status_label || labels[status || ''] || status || '-';
}

function empty(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

async function loadData() {
  if (!rechargeId.value) {
    message.error('充值订单 ID 不正确');
    return;
  }
  loading.value = true;
  try {
    detail.value = await getDashboardRechargeDetailApi(rechargeId.value);
    selectedStatus.value = detail.value.status || '';
  } catch {
    detail.value = null;
    selectedStatus.value = '';
  } finally {
    loading.value = false;
  }
}

async function saveStatus() {
  if (!requireCloudDangerPermission('保存充值订单状态')) return;
  if (!detail.value || !selectedStatus.value) {
    return;
  }
  saving.value = true;
  try {
    detail.value = await updateDashboardRechargeStatusApi(detail.value.id, {
      status: selectedStatus.value,
    });
    selectedStatus.value = detail.value.status || '';
    message.success('充值订单状态已更新');
  } catch (error: any) {
    message.error(error?.message || '更新充值订单状态失败');
  } finally {
    saving.value = false;
  }
}

function goBack() {
  router.push('/admin/cloud-orders/recharges').catch(() => {});
}

onMounted(loadData);
</script>

<template>
  <Page description="查看充值订单完整信息" title="充值订单详情">
    <Card :loading="loading">
      <template #title>
        <Space>
          <Button size="small" @click="goBack">返回充值订单</Button>
          <span>充值订单 #{{ detail?.id || rechargeId }}</span>
          <Select
            v-if="detail"
            v-model:value="selectedStatus"
            :options="statusOptions"
            :disabled="!canRunCloudDanger"
            style="width: 160px"
          />
          <Button
            v-if="detail"
            :disabled="!canRunCloudDanger"
            :loading="saving"
            size="small"
            type="primary"
            @click="saveStatus"
          >
            保存状态
          </Button>
        </Space>
      </template>

      <template v-if="detail">
        <Descriptions bordered :column="2" size="small" title="基础信息">
          <Descriptions.Item label="充值订单 ID">
            {{ detail.id }}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag :color="statusColor(detail.status)">
              {{ statusLabel(detail.status) }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="用户">
            {{ empty(detail.user_display_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="用户名">
            {{ empty(detail.username_label) }}
          </Descriptions.Item>
          <Descriptions.Item label="Telegram ID">
            {{ empty(detail.tg_user_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="后台用户 ID">
            {{ empty(detail.user_id) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="金额信息"
        >
          <Descriptions.Item label="币种">
            {{ empty(detail.currency) }}
          </Descriptions.Item>
          <Descriptions.Item label="充值金额">
            {{ empty(detail.amount) }}
          </Descriptions.Item>
          <Descriptions.Item label="应付金额">
            {{ empty(detail.pay_amount) }}
          </Descriptions.Item>
          <Descriptions.Item label="收款地址" :span="2">
            <Typography.Paragraph
              :copyable="
                detail.receive_address
                  ? { text: detail.receive_address }
                  : false
              "
              class="!mb-0 break-all"
            >
              {{ empty(detail.receive_address) }}
            </Typography.Paragraph>
          </Descriptions.Item>
          <Descriptions.Item label="交易哈希" :span="2">
            <Typography.Paragraph
              :copyable="detail.tx_hash ? { text: detail.tx_hash } : false"
              class="!mb-0 break-all"
            >
              {{ empty(detail.tx_hash) }}
            </Typography.Paragraph>
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="时间信息"
        >
          <Descriptions.Item label="创建时间">
            {{ empty(detail.created_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {{ empty(detail.completed_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {{ empty(detail.updated_at) }}
          </Descriptions.Item>
        </Descriptions>
      </template>

      <Empty v-else-if="!loading" description="未找到充值订单详情" />
    </Card>
  </Page>
</template>
