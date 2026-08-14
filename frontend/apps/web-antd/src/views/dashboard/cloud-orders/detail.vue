<script lang="ts" setup>
import type { DashboardCloudOrderDetail } from '#/api/admin';

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
  getDashboardCloudOrderDetailApi,
  getDashboardCloudOrderLoginSecretsApi,
  updateDashboardCloudOrderStatusApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const route = useRoute();
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const saving = ref(false);
const detailRefreshing = ref(false);
const detail = ref<DashboardCloudOrderDetail | null>(null);
const selectedStatus = ref<string>('');
const loginSecretsLoading = ref(false);
const revealedLoginPassword = ref('');
const revealedLoginUser = ref('');

const orderId = computed(() => Number(route.params.id || 0));
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

function statusColor(status?: string) {
  if (['completed', 'paid'].includes(status || '')) return 'green';
  if (
    ['expiring', 'pending', 'provisioning', 'renew_pending'].includes(
      status || '',
    )
  )
    return 'orange';
  if (['cancelled', 'deleted', 'expired', 'failed'].includes(status || ''))
    return 'red';
  return 'blue';
}

function statusLabel(status?: string) {
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
  return labels[status || ''] || status || '-';
}

function providerLabel(provider?: string) {
  const labels: Record<string, string> = {
    aliyun_simple: '阿里云',
    aws_lightsail: 'AWS Lightsail',
  };
  return labels[provider || ''] || provider || '-';
}

function empty(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function sourceTagColor(source?: string) {
  if (source === 'manual_owner_change') return 'purple';
  if (source === 'manual_expiry_change') return 'gold';
  if (source === 'manual_price_change') return 'cyan';
  if (source === 'manual_owner_expiry_change') return 'magenta';
  if (source === 'renewal' || source === 'renewal_rebuild') return 'blue';
  return 'default';
}

function orderSourceItems(item?: DashboardCloudOrderDetail | null) {
  if (!item) return [] as Array<{ key: string; label: string }>;
  const tagKeys = item.order_source_tags || [];
  const tagLabels = item.order_source_tag_labels || [];
  if (tagLabels.length > 0) {
    return tagLabels.map((label, index) => ({
      key: tagKeys[index] || item.order_source || label,
      label,
    }));
  }
  return item.order_source_label
    ? [
        {
          key: item.order_source || item.order_source_label,
          label: item.order_source_label,
        },
      ]
    : [];
}

async function loadData(options?: { silent?: boolean }) {
  if (!orderId.value) {
    message.error('订单 ID 不正确');
    return;
  }
  if (options?.silent) {
    detailRefreshing.value = true;
  } else {
    loading.value = true;
  }
  try {
    detail.value = await getDashboardCloudOrderDetailApi(orderId.value);
    selectedStatus.value = detail.value.status || '';
    revealedLoginPassword.value = '';
    revealedLoginUser.value = '';
  } catch {
    detail.value = null;
    selectedStatus.value = '';
    revealedLoginPassword.value = '';
    revealedLoginUser.value = '';
  } finally {
    loading.value = false;
    detailRefreshing.value = false;
  }
}

async function saveStatus() {
  if (!requireCloudDangerPermission('保存云订单状态')) return;
  if (!detail.value || !selectedStatus.value || saving.value) {
    return;
  }
  saving.value = true;
  message.loading({
    content: '正在保存状态...',
    key: 'cloud-order-status',
    duration: 0,
  });
  try {
    detail.value = await updateDashboardCloudOrderStatusApi(detail.value.id, {
      status: selectedStatus.value,
    });
    selectedStatus.value = detail.value.status || '';
    message.success({ content: '订单状态已更新', key: 'cloud-order-status' });
    void loadData({ silent: true });
  } catch (error: any) {
    message.error({
      content: error?.message || '更新订单状态失败',
      key: 'cloud-order-status',
    });
  } finally {
    saving.value = false;
  }
}

async function revealLoginSecrets() {
  if (!detail.value || loginSecretsLoading.value) return;
  loginSecretsLoading.value = true;
  try {
    const secrets = await getDashboardCloudOrderLoginSecretsApi(
      detail.value.id,
    );
    revealedLoginUser.value = secrets.login_user || '';
    revealedLoginPassword.value = secrets.login_password || '';
    if (!revealedLoginPassword.value) {
      message.warning('当前订单没有登录密码');
    }
  } catch (error: any) {
    message.error(error?.message || '获取登录信息失败');
  } finally {
    loginSecretsLoading.value = false;
  }
}

async function copyLoginInfo() {
  const lines = [
    detail.value?.public_ip ? `IP: ${detail.value.public_ip}` : '',
    `账号: ${revealedLoginUser.value || detail.value?.login_user || '-'}`,
    revealedLoginPassword.value ? `密码: ${revealedLoginPassword.value}` : '',
  ].filter(Boolean);
  if (lines.length === 0) {
    message.warning('没有可复制的登录信息');
    return;
  }
  await navigator.clipboard.writeText(lines.join('\n'));
  message.success('已复制登录信息');
}

function goBack() {
  router.push('/admin/cloud-orders').catch(() => {});
}

onMounted(loadData);
</script>

<template>
  <Page description="查看订单完整信息" title="订单详情">
    <Card :loading="loading">
      <template #title>
        <Space>
          <Button size="small" @click="goBack">返回订单列表</Button>
          <span>{{ detail?.order_no || `订单 #${orderId}` }}</span>
          <Select
            v-if="detail"
            v-model:value="selectedStatus"
            :options="statusOptions"
            :disabled="saving || !canRunCloudDanger"
            style="width: 180px"
          />
          <Button
            v-if="detail"
            :disabled="!canRunCloudDanger"
            :loading="saving"
            size="small"
            type="primary"
            @click="saveStatus"
          >
            {{ saving ? '保存中...' : '保存状态' }}
          </Button>
          <Tag v-if="detailRefreshing" color="processing">刷新中</Tag>
        </Space>
      </template>

      <template v-if="detail">
        <Descriptions bordered :column="2" size="small" title="基础信息">
          <Descriptions.Item label="订单号">
            {{ detail.order_no }}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag :color="statusColor(detail.status)">
              {{ statusLabel(detail.status) }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="来源">
            <Space :size="4" wrap>
              <Tag
                v-for="tag in orderSourceItems(detail)"
                :key="tag.key"
                :color="sourceTagColor(tag.key)"
              >
                {{ tag.label }}
              </Tag>
              <span v-if="orderSourceItems(detail).length === 0">-</span>
            </Space>
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
          <Descriptions.Item label="厂商">
            {{ providerLabel(detail.provider) }}
          </Descriptions.Item>
          <Descriptions.Item label="地区">
            {{ empty(detail.region_label || detail.region_name) }} /
            {{ empty(detail.region_code) }}
          </Descriptions.Item>
          <Descriptions.Item label="套餐">
            {{ empty(detail.plan_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="数量">
            {{ empty(detail.quantity) }}
          </Descriptions.Item>
          <Descriptions.Item label="金额">
            {{ empty(detail.total_amount) }}
            {{ empty(detail.currency) }}
          </Descriptions.Item>
          <Descriptions.Item label="应付金额">
            {{ empty(detail.pay_amount) }}
          </Descriptions.Item>
          <Descriptions.Item label="支付方式">
            {{ empty(detail.pay_method) }}
          </Descriptions.Item>
          <Descriptions.Item label="交易哈希" :span="2">
            {{ empty(detail.tx_hash) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="服务器信息"
        >
          <Descriptions.Item label="服务器名">
            {{ empty(detail.server_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="实例 ID">
            {{ empty(detail.instance_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="云资源 ID">
            {{ empty(detail.provider_resource_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="公网 IP">
            {{ empty(detail.public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item label="历史公网 IP">
            {{ empty(detail.previous_public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item label="固定 IP 名称">
            {{ empty(detail.static_ip_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="登录账号">
            {{ empty(revealedLoginUser || detail.login_user) }}
          </Descriptions.Item>
          <Descriptions.Item label="登录密码">
            <Space wrap>
              <Typography.Text class="font-mono">
                {{ empty(revealedLoginPassword || detail.login_password) }}
              </Typography.Text>
              <Button
                :disabled="detail.status === 'deleted'"
                :loading="loginSecretsLoading"
                size="small"
                @click="revealLoginSecrets"
              >
                {{ revealedLoginPassword ? '重新获取' : '显示登录信息' }}
              </Button>
              <Button
                v-if="revealedLoginPassword"
                size="small"
                @click="copyLoginInfo"
              >
                复制
              </Button>
            </Space>
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="代理信息"
        >
          <Descriptions.Item label="MTProxy 主机">
            {{ empty(detail.mtproxy_host) }}
          </Descriptions.Item>
          <Descriptions.Item label="MTProxy 端口">
            {{ empty(detail.mtproxy_port) }}
          </Descriptions.Item>
          <Descriptions.Item label="MTProxy 密钥" :span="2">
            {{ empty(detail.mtproxy_secret) }}
          </Descriptions.Item>
          <Descriptions.Item label="MTProxy 链接" :span="2">
            <Typography.Paragraph
              :copyable="
                detail.mtproxy_link ? { text: detail.mtproxy_link } : false
              "
              class="!mb-0 break-all"
            >
              {{ empty(detail.mtproxy_link) }}
            </Typography.Paragraph>
          </Descriptions.Item>
        </Descriptions>

        <Card
          v-if="detail.proxy_links?.length"
          class="mt-4"
          size="small"
          title="全部代理链路"
        >
          <div
            v-for="(item, index) in detail.proxy_links"
            :key="`${item.url}-${index}`"
            class="mb-3 last:mb-0"
          >
            <div class="mb-1 text-sm opacity-75">
              {{ item.name || `链路 ${index + 1}` }}
            </div>
            <Typography.Paragraph
              :copyable="{ text: item.url }"
              class="!mb-0 break-all font-mono"
            >
              {{ item.url }}
            </Typography.Paragraph>
          </div>
        </Card>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="生命周期"
        >
          <Descriptions.Item label="有效期天数">
            {{ empty(detail.lifecycle_days) }}
          </Descriptions.Item>
          <Descriptions.Item label="最后续费时间">
            {{ empty(detail.last_renewed_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="服务开始时间">
            {{ empty(detail.service_started_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="服务到期时间">
            {{ empty(detail.actual_expires_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="续费宽限到期">
            {{ empty(detail.renew_grace_expires_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="计划关机时间">
            {{ empty(detail.suspend_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="计划删机时间">
            {{ empty(detail.delete_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="IP 保留到期">
            {{ empty(detail.ip_recycle_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {{ empty(detail.created_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="支付时间">
            {{ empty(detail.paid_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {{ empty(detail.completed_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="过期时间">
            {{ empty(detail.expired_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间" :span="2">
            {{ empty(detail.updated_at) }}
          </Descriptions.Item>
        </Descriptions>

        <Card class="mt-4" size="small" title="创建说明">
          <Typography.Paragraph class="!mb-0 whitespace-pre-wrap break-all">
            {{ empty(detail.provision_note) }}
          </Typography.Paragraph>
        </Card>
      </template>

      <Empty v-else-if="!loading" description="未找到订单详情" />
    </Card>
  </Page>
</template>
