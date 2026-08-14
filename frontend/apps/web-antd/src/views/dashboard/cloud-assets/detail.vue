<script lang="ts" setup>
import type {
  DashboardCloudActionSwitchItem,
  DashboardCloudAssetDetail,
  DashboardCloudOrderSummaryItem,
  DashboardSiteConfigGroupItem,
} from '#/api/admin';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  Empty,
  message,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getDashboardCloudAssetDetailApi,
  getDashboardSiteConfigGroupsApi,
  updateDashboardCloudAssetApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const route = useRoute();
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const lifecycleSwitchSaving = ref<
  Partial<
    Record<
      'ip_delete_enabled' | 'server_delete_enabled' | 'shutdown_enabled',
      boolean
    >
  >
>({});
const detail = ref<DashboardCloudAssetDetail | null>(null);
const expandedLifecycleRows = ref<Record<string, boolean>>({});
const actionSwitchItems = ref<DashboardCloudActionSwitchItem[]>([]);

const assetId = computed(() => Number(route.params.id || 0));
const historyOrders = computed<DashboardCloudOrderSummaryItem[]>(
  () => detail.value?.history_orders || [],
);
type LifecycleSwitchField =
  | 'ip_delete_enabled'
  | 'server_delete_enabled'
  | 'shutdown_enabled';

function actionSwitchLabel(key: string) {
  if (key === 'cloud_server_shutdown_enabled') return '关机服务器';
  if (key === 'cloud_server_delete_enabled') return '删除服务器';
  if (key === 'cloud_ip_delete_enabled') return '删除IP';
  return key;
}

function toActionSwitchItem(item: DashboardSiteConfigGroupItem) {
  return {
    description: item.description || '',
    enabled: String(item.value || '').trim() === '1',
    id: item.id,
    key: item.key,
    label: actionSwitchLabel(item.key),
  };
}

function globalActionSwitchKey(field: LifecycleSwitchField) {
  if (field === 'shutdown_enabled') return 'cloud_server_shutdown_enabled';
  if (field === 'server_delete_enabled') return 'cloud_server_delete_enabled';
  return 'cloud_ip_delete_enabled';
}

function globalActionSwitchLabel(field: LifecycleSwitchField) {
  if (field === 'shutdown_enabled') return '关机服务器';
  if (field === 'server_delete_enabled') return '删除服务器';
  return '删除IP';
}

const actionSwitchEnabledMap = computed(() =>
  Object.fromEntries(
    actionSwitchItems.value.map((item) => [item.key, item.enabled]),
  ),
);

function isGlobalActionEnabled(field: LifecycleSwitchField) {
  return actionSwitchEnabledMap.value[globalActionSwitchKey(field)] !== false;
}

function lifecycleSwitchDisabled(field: LifecycleSwitchField) {
  return !canRunCloudDanger.value || !isGlobalActionEnabled(field);
}

const lifecycleColumns = [
  {
    title: '执行时间',
    dataIndex: 'executed_at',
    key: 'executed_at',
    width: 170,
  },
  {
    title: '触发事件',
    dataIndex: 'trigger_label',
    key: 'trigger_label',
    width: 110,
  },
  { title: '事件', dataIndex: 'event_label', key: 'event_label', width: 110 },
  {
    title: '服务器名',
    dataIndex: 'server_name',
    key: 'server_name',
    width: 180,
  },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 220 },
  { title: '当前 IP', dataIndex: 'public_ip', key: 'public_ip', width: 140 },
  {
    title: '上一个 IP',
    dataIndex: 'previous_public_ip',
    key: 'previous_public_ip',
    width: 140,
  },
  { title: '说明', dataIndex: 'summary', key: 'summary' },
];

function empty(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function usernamePipeText(value?: null | string) {
  const raw = String(value || '').trim();
  if (!raw || raw === '-') return '-';
  return raw
    .split(/\s*[/|｜]\s*/)
    .map((item) => item.trim())
    .filter(Boolean)
    .join('｜');
}

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function formatExpiryTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function statusColor(status?: string) {
  if (['completed', 'paid', 'running'].includes(status || '')) return 'green';
  if (
    [
      'expiring',
      'pending',
      'provisioning',
      'renew_pending',
      'unknown',
    ].includes(status || '')
  )
    return 'orange';
  if (['deleted', 'expired', 'failed', 'terminated'].includes(status || ''))
    return 'red';
  return 'blue';
}

async function loadData() {
  if (!assetId.value) {
    message.error('代理 ID 不正确');
    return;
  }
  loading.value = true;
  try {
    const [assetDetail, groups] = await Promise.all([
      getDashboardCloudAssetDetailApi(assetId.value),
      getDashboardSiteConfigGroupsApi({
        group: 'cloud_actions',
      }),
    ]);
    detail.value = assetDetail;
    actionSwitchItems.value = (groups[0]?.items || []).map((groupItem) =>
      toActionSwitchItem(groupItem),
    );
  } catch (error: any) {
    detail.value = null;
    message.error(error?.message || '加载代理详情失败');
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push('/admin/cloud-assets').catch(() => {});
}

async function toggleLifecycleSwitch(
  field: LifecycleSwitchField,
  label: string,
  checked: boolean,
) {
  if (!detail.value || lifecycleSwitchSaving.value[field]) return;
  if (!requireCloudDangerPermission(`切换${label}`)) return;
  if (!isGlobalActionEnabled(field)) {
    message.error(
      `${globalActionSwitchLabel(field)}总开关当前为关闭状态，需先到生命周期计划页开启后再切换单项计划。`,
    );
    return;
  }
  lifecycleSwitchSaving.value = {
    ...lifecycleSwitchSaving.value,
    [field]: true,
  };
  try {
    const result = await updateDashboardCloudAssetApi(detail.value.id, {
      [field]: checked,
    });
    detail.value[field] = result[field] !== false;
    detail.value.risk_status = result.risk_status;
    detail.value.risk_statuses = result.risk_statuses;
    detail.value.risk_reasons = result.risk_reasons;
    message.success(`${label}已${detail.value[field] ? '开启' : '关闭'}`);
  } catch (error: any) {
    message.error(error?.message || `${label}切换失败`);
  } finally {
    lifecycleSwitchSaving.value = {
      ...lifecycleSwitchSaving.value,
      [field]: false,
    };
  }
}

const canOpenOrder = Boolean;

function openOrder(path?: null | string) {
  if (!path) {
    return;
  }
  router.push(path).catch(() => {});
}

function historyOrderTagColor(status?: string) {
  if (['completed', 'paid'].includes(status || '')) return 'green';
  if (
    ['expiring', 'provisioning', 'renew_pending', 'suspended'].includes(
      status || '',
    )
  )
    return 'orange';
  if (['cancelled', 'deleted', 'expired', 'failed'].includes(status || ''))
    return 'red';
  return 'blue';
}

function historySourceTagColor(source?: string) {
  if (source === 'manual_owner_change') return 'purple';
  if (source === 'manual_expiry_change') return 'gold';
  if (source === 'manual_price_change') return 'cyan';
  if (source === 'manual_owner_expiry_change') return 'magenta';
  if (source === 'renewal' || source === 'renewal_rebuild') return 'blue';
  return 'default';
}

function historyOrderIpChange(item?: DashboardCloudOrderSummaryItem | null) {
  const previousIp = String(item?.previous_public_ip || '').trim();
  const currentIp = String(item?.public_ip || '').trim();
  if (previousIp && currentIp && previousIp !== currentIp)
    return `${previousIp} → ${currentIp}`;
  return previousIp || currentIp || '';
}

function orderSourceItems(item?: DashboardCloudOrderSummaryItem | null) {
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

function lifecycleOrderPath(orderNo?: string) {
  const value = String(orderNo || '').trim();
  if (!value || value === '-') return '';
  return detail.value?.lifecycle_order_links?.[value] || '';
}

function parseLifecycleLine(line: string, fallbackEvent?: string) {
  const text = String(line || '').trim();
  if (!text) return null;
  const executedAt =
    text.match(/执行时间：(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/)?.[1] || '';
  const publicIp = text.match(/IP：([^；]+)/)?.[1] || '';
  const triggerLabel = text.match(/触发事件：([^；]+)/)?.[1] || '';
  const orderNo = text.match(/订单号：([^；]+)/)?.[1] || '';
  const serverName = text.match(/服务器名：([^；]+)/)?.[1] || '';
  const previousPublicIp =
    text.match(/上一个IP：([^；]+)/)?.[1] ||
    text.match(/旧IP[=：]([^；]+)/)?.[1] ||
    text.match(/原固定\/旧IP\s*([^；]+)/)?.[1] ||
    text.match(/旧固定IP\s*([^；\s]+)/)?.[1] ||
    text.match(/自动同步发现 IP 变化：([^\s；]+)\s*->/)?.[1] ||
    text.match(/固定 IP ([^\s；]+) 从/)?.[1] ||
    (publicIp && text.includes('固定 IP 保留期结束') ? publicIp : '');
  const summary = text.match(/执行内容：(.+)$/)?.[1] || text;

  let eventLabel = fallbackEvent || '变更';
  if (summary.includes('开始创建服务器')) eventLabel = '创建开始';
  else if (
    summary.includes('云端实例已创建') ||
    summary.includes('触发创建云端实例')
  )
    eventLabel = '实例创建';
  else if (summary.includes('创建并分配IP')) eventLabel = '分配IP';
  else if (summary.includes('执行关机')) eventLabel = '关机';
  else if (summary.includes('执行删除') || summary.includes('实例已删除'))
    eventLabel = '删除';
  else if (summary.includes('固定 IP 已真实释放') || summary.includes('已回收'))
    eventLabel = '回收';
  else if (
    summary.includes('旧服务器生命周期') ||
    summary.includes('旧机日期已调整')
  )
    eventLabel = '旧机安排';
  else if (summary.includes('续费')) eventLabel = '续费';

  return {
    id: `${executedAt}-${triggerLabel}-${eventLabel}-${publicIp}-${summary}`,
    executed_at: executedAt,
    trigger_label: triggerLabel || '-',
    event_label: eventLabel,
    order_no: orderNo || '-',
    order_link_path: lifecycleOrderPath(orderNo),
    server_name: serverName || '-',
    public_ip: publicIp || '-',
    previous_public_ip: previousPublicIp || '-',
    summary,
  };
}

const lifecycleRows = computed(() => {
  const rows: Array<Record<string, string>> = [];
  for (const item of detail.value?.ip_logs || []) {
    const lines = String(item.note || '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    for (const line of lines) {
      const parsed = parseLifecycleLine(
        line,
        item.event_label || item.event_type,
      );
      if (parsed) rows.push(parsed);
    }
  }
  return rows;
});

function lifecycleSummaryTooLong(text?: null | string) {
  const value = String(text || '').trim();
  if (!value) return false;
  return value.length > 100 || value.split('\n').filter(Boolean).length > 2;
}

function lifecycleExpanded(record: Record<string, string>) {
  return Boolean(expandedLifecycleRows.value[String(record.id || '')]);
}

function toggleLifecycleSummary(record: Record<string, string>) {
  const key = String(record.id || '');
  expandedLifecycleRows.value[key] = !expandedLifecycleRows.value[key];
}

onMounted(loadData);
</script>

<template>
  <Page description="查看代理、云账号、IP 与生命周期日志" title="代理详情">
    <Card :loading="loading">
      <template #title>
        <Space>
          <Button size="small" @click="goBack">返回代理列表</Button>
          <span>{{ detail?.asset_name || `代理 #${assetId}` }}</span>
          <Tag v-if="detail" :color="statusColor(detail.status)">
            {{ detail.status_label || detail.status }}
          </Tag>
          <Button v-if="detail" size="small" @click="loadData">刷新</Button>
        </Space>
      </template>

      <template v-if="detail">
        <Descriptions bordered :column="2" size="small" title="基础信息">
          <Descriptions.Item label="资产 ID">{{ detail.id }}</Descriptions.Item>
          <Descriptions.Item label="类型">{{ detail.kind }}</Descriptions.Item>
          <Descriptions.Item label="资产名称">
            {{ empty(detail.asset_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="来源">
            {{ empty(detail.source_label || detail.source) }}
          </Descriptions.Item>
          <Descriptions.Item label="厂商">
            {{ empty(detail.provider_label || detail.provider) }}
          </Descriptions.Item>
          <Descriptions.Item label="地区">
            {{ empty(detail.region_label || detail.region_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="云账号ID" :span="2">
            <Typography.Paragraph
              :copyable="
                detail.account_label ? { text: detail.account_label } : false
              "
              class="!mb-0 break-all font-mono"
            >
              {{ empty(detail.account_label) }}
            </Typography.Paragraph>
          </Descriptions.Item>
          <Descriptions.Item label="内部云账号记录 ID">
            {{ empty(detail.cloud_account_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="排序">
            {{ empty(detail.sort_order) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="服务器与 IP"
        >
          <Descriptions.Item label="公网 IP">
            {{ empty(detail.public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item label="实例 ID">
            {{ empty(detail.instance_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="云资源 ID" :span="2">
            <Typography.Paragraph
              :copyable="
                detail.provider_resource_id
                  ? { text: detail.provider_resource_id }
                  : false
              "
              class="!mb-0 break-all font-mono"
            >
              {{ empty(detail.provider_resource_id) }}
            </Typography.Paragraph>
          </Descriptions.Item>
          <Descriptions.Item label="固定 IP 名称">
            {{ empty(detail.static_ip_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="上一个 IP">
            {{ empty(detail.previous_public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item label="到期时间">
            {{ formatExpiryTime(detail.actual_expires_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="关机计划">
            <Switch
              :checked="detail.shutdown_enabled !== false"
              :disabled="lifecycleSwitchDisabled('shutdown_enabled')"
              :loading="lifecycleSwitchSaving.shutdown_enabled"
              checked-children="开"
              un-checked-children="关"
              @change="
                (checked) =>
                  toggleLifecycleSwitch(
                    'shutdown_enabled',
                    '关机计划',
                    Boolean(checked),
                  )
              "
            />
          </Descriptions.Item>
          <Descriptions.Item label="删除计划">
            <Switch
              :checked="detail.server_delete_enabled !== false"
              :disabled="lifecycleSwitchDisabled('server_delete_enabled')"
              :loading="lifecycleSwitchSaving.server_delete_enabled"
              checked-children="开"
              un-checked-children="关"
              @change="
                (checked) =>
                  toggleLifecycleSwitch(
                    'server_delete_enabled',
                    '删除计划',
                    Boolean(checked),
                  )
              "
            />
          </Descriptions.Item>
          <Descriptions.Item label="IP 删除计划">
            <Switch
              :checked="detail.ip_delete_enabled !== false"
              :disabled="lifecycleSwitchDisabled('ip_delete_enabled')"
              :loading="lifecycleSwitchSaving.ip_delete_enabled"
              checked-children="开"
              un-checked-children="关"
              @change="
                (checked) =>
                  toggleLifecycleSwitch(
                    'ip_delete_enabled',
                    'IP 删除计划',
                    Boolean(checked),
                  )
              "
            />
          </Descriptions.Item>
          <Descriptions.Item label="同步状态">
            {{ empty(detail.provider_status) }}
          </Descriptions.Item>
          <Descriptions.Item label="最近同步时间">
            {{ formatTime(detail.provider_checked_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {{ formatTime(detail.created_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {{ formatTime(detail.updated_at) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          :column="2"
          class="mt-4"
          size="small"
          title="用户与订单"
        >
          <Descriptions.Item label="用户">
            {{ empty(detail.user_display_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="用户名">
            {{ usernamePipeText(detail.username_label) }}
          </Descriptions.Item>
          <Descriptions.Item label="Telegram ID">
            {{ empty(detail.tg_user_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="后台用户 ID">
            {{ empty(detail.user_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="订单号">
            <Space v-if="detail.order_no">
              <span>{{ detail.order_no }}</span>
              <Button
                v-if="canOpenOrder(detail.order_link_path)"
                size="small"
                type="link"
                @click="openOrder(detail.order_link_path)"
              >
                查看订单
              </Button>
            </Space>
            <span v-else>{{ empty(detail.order_no) }}</span>
          </Descriptions.Item>
          <Descriptions.Item label="订单状态">
            {{ empty(detail.order_status_label || detail.order_status) }}
          </Descriptions.Item>
          <Descriptions.Item label="价格">
            {{ empty(detail.price) }}
            {{ empty(detail.currency) }}
          </Descriptions.Item>
          <Descriptions.Item label="资产状态">
            <Tag :color="statusColor(detail.status)">
              {{ empty(detail.status_label || detail.status) }}
            </Tag>
          </Descriptions.Item>
        </Descriptions>

        <Card class="mt-4" size="small" title="关联订单">
          <template v-if="detail.related_order">
            <Descriptions bordered :column="2" size="small">
              <Descriptions.Item label="订单号">
                <Space>
                  <span>{{ detail.related_order.order_no }}</span>
                  <Button
                    v-if="canOpenOrder(detail.related_order.order_link_path)"
                    size="small"
                    type="link"
                    @click="openOrder(detail.related_order.order_link_path)"
                  >
                    跳转
                  </Button>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space wrap>
                  <Tag
                    :color="historyOrderTagColor(detail.related_order.status)"
                  >
                    {{
                      detail.related_order.status_label ||
                      detail.related_order.status
                    }}
                  </Tag>
                  <Tag
                    v-for="tag in orderSourceItems(detail.related_order)"
                    :key="tag.key"
                    :color="historySourceTagColor(tag.key)"
                  >
                    {{ tag.label }}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="公网 IP">
                {{ empty(detail.related_order.public_ip) }}
              </Descriptions.Item>
              <Descriptions.Item label="服务到期">
                {{ formatExpiryTime(detail.related_order.actual_expires_at) }}
              </Descriptions.Item>
            </Descriptions>
          </template>
          <Empty v-else description="暂无关联订单" />
        </Card>

        <Card class="mt-4" size="small" title="历史订单">
          <template v-if="historyOrders.length > 0">
            <div
              v-for="item in historyOrders"
              :key="item.id"
              class="mb-3 rounded border border-solid border-gray-200 p-3 last:mb-0"
            >
              <Space class="mb-2" wrap>
                <span class="font-medium">{{ item.order_no }}</span>
                <Tag :color="historyOrderTagColor(item.status)">
                  {{ item.status_label || item.status }}
                </Tag>
                <Tag
                  v-for="tag in orderSourceItems(item)"
                  :key="`${item.id}-${tag.key}-${tag.label}`"
                  :color="historySourceTagColor(tag.key)"
                >
                  {{ tag.label }}
                </Tag>
                <Tag v-if="item.id === detail.order_id" color="processing">
                  当前关联
                </Tag>
                <Button
                  v-if="canOpenOrder(item.order_link_path)"
                  size="small"
                  type="link"
                  @click="openOrder(item.order_link_path)"
                >
                  查看
                </Button>
              </Space>
              <div
                class="grid grid-cols-1 gap-2 text-sm text-gray-500 md:grid-cols-3"
              >
                <div>公网 IP：{{ empty(item.public_ip) }}</div>
                <div>IP 变更：{{ empty(historyOrderIpChange(item)) }}</div>
                <div>到期：{{ formatExpiryTime(item.actual_expires_at) }}</div>
                <div>创建：{{ formatTime(item.created_at) }}</div>
              </div>
            </div>
          </template>
          <Empty v-else description="暂无历史订单" />
        </Card>

        <Card class="mt-4" size="small" title="IP / 生命周期日志">
          <Table
            :columns="lifecycleColumns"
            :data-source="lifecycleRows"
            :pagination="false"
            row-key="id"
            size="small"
            :scroll="{ x: 1100 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'executed_at'">
                {{ empty(record.executed_at) }}
              </template>
              <template v-else-if="column.key === 'order_no'">
                <Button
                  v-if="record.order_link_path"
                  class="!px-0"
                  type="link"
                  @click="openOrder(record.order_link_path)"
                >
                  {{ empty(record.order_no) }}
                </Button>
                <span v-else>{{ empty(record.order_no) }}</span>
              </template>
              <template v-else-if="column.key === 'summary'">
                <div class="flex flex-col gap-2">
                  <Typography.Paragraph
                    class="!mb-0 whitespace-pre-wrap break-all"
                    :class="[
                      !lifecycleExpanded(record) &&
                      lifecycleSummaryTooLong(record.summary)
                        ? 'collapsed-note'
                        : '',
                    ]"
                  >
                    {{ empty(record.summary) }}
                  </Typography.Paragraph>
                  <Button
                    v-if="lifecycleSummaryTooLong(record.summary)"
                    size="small"
                    type="link"
                    @click="toggleLifecycleSummary(record)"
                  >
                    {{ lifecycleExpanded(record) ? '收起' : '展开' }}
                  </Button>
                </div>
              </template>
            </template>
          </Table>
        </Card>
      </template>

      <Empty v-else-if="!loading" description="未找到代理详情" />
    </Card>
  </Page>
</template>

<style scoped>
.collapsed-note {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
</style>
