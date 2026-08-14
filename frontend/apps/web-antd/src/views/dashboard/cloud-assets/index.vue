<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudAssetDetail,
  DashboardCloudAssetGroup,
  DashboardCloudAssetGroupedResponse,
  DashboardCloudAssetItem,
  DashboardCloudAssetsSyncStatus,
  DashboardCloudAssetSyncJob,
  DashboardCloudAssetSyncJobEvent,
  DashboardCloudAssetSyncJobsMetrics,
  DashboardCloudAssetUpdatePayload,
  DashboardCloudOrderSummaryItem,
  DashboardTelegramGroupFilterItem,
} from '#/api/admin';

import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Collapse,
  DatePicker,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Pagination,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  TypographyParagraph,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  cancelDashboardCloudAssetSyncJobApi,
  deleteDashboardCloudAssetApi,
  getDashboardCloudAssetDetailApi,
  getDashboardCloudAssetRiskSummaryApi,
  getDashboardCloudAssetsGroupedPageApi,
  getDashboardCloudAssetsPageApi,
  getDashboardCloudAssetsSyncStatusApi,
  getDashboardCloudAssetSyncJobApi,
  getDashboardCloudAssetSyncJobMetricsApi,
  getDashboardCloudAssetSyncJobsApi,
  getDashboardTelegramGroupsApi,
  refreshDashboardCloudAssetTrafficApi,
  retryDashboardCloudAssetSyncJobApi,
  runDashboardCloudAssetSpeedTestApi,
  syncDashboardCloudAssetsApi,
  syncDashboardCloudAssetStatusApi,
  toggleDashboardCloudAssetAutoRenewApi,
  updateDashboardCloudAssetApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const DEFAULT_AUTO_REFRESH_SECONDS = 5 * 60 * 60;
const ASSET_PAGE_SIZE = 20;

const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const saving = ref(false);
const syncing = ref(false);
const syncScope = ref<'aliyun' | 'all' | 'aws' | 'selected'>('all');
const lastSyncTasks = ref<any[]>([]);
const lastSkippedSyncTasks = ref<any[]>([]);
const activeSyncJob = ref<DashboardCloudAssetSyncJob | null>(null);
const syncJobsOpen = ref(false);
const syncJobsLoading = ref(false);
const syncJobs = ref<DashboardCloudAssetSyncJob[]>([]);
const syncJobMetrics = ref<DashboardCloudAssetSyncJobsMetrics | null>(null);
const syncJobMetricsLoading = ref(false);
const syncJobsStatusFilter = ref('all');
const syncJobsFailedOnly = ref(false);
const syncJobRetryingIds = ref<number[]>([]);
const syncJobCancellingIds = ref<number[]>([]);
const assetSyncingIds = ref<number[]>([]);
const networkSpeedTestingIds = ref<number[]>([]);
const networkTrafficLoadingIds = ref<number[]>([]);
const autoRenewSavingIds = ref<number[]>([]);
const keyword = ref('');
const grouped = ref(true);
const showDeletedAssets = ref(false);
const groupMode = ref<'telegram_group' | 'user'>('telegram_group');
type AssetDisplayMode = 'flat' | 'telegram_group' | 'user';
const totalSortMode = ref<
  | 'default'
  | 'expires_asc'
  | 'expires_desc'
  | 'remaining_asc'
  | 'remaining_desc'
>('default');
const lastRefreshedAt = ref<dayjs.Dayjs | null>(null);
const lastSyncedAt = ref<dayjs.Dayjs | null>(null);
const nextRefreshInSeconds = ref(DEFAULT_AUTO_REFRESH_SECONDS);
const recentSyncHighlight = ref(false);
const autoSyncEverySeconds = ref(DEFAULT_AUTO_REFRESH_SECONDS);
const awsExistingCount = ref(0);
const aliyunExistingCount = ref(0);
const unattachedIpCount = ref(0);
const items = ref<DashboardCloudAssetItem[]>([]);
const groups = ref<DashboardCloudAssetGroup[]>([]);
const riskStatus = ref('all');
const riskCounts = ref<Record<string, number>>({});
const selectedRowKeys = ref<number[]>([]);
const telegramGroups = ref<DashboardTelegramGroupFilterItem[]>([]);
const loadingMore = ref(false);
const loadProgress = reactive({
  done: true,
  loaded: 0,
  pageSize: ASSET_PAGE_SIZE,
  total: 0,
});
const groupPagination = reactive({
  page: 1,
  pageSize: ASSET_PAGE_SIZE,
  total: 0,
});
const assetPagination = reactive({
  page: 1,
  pageSize: ASSET_PAGE_SIZE,
  total: 0,
});
const syncJobsPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
});
const expandedGroupKeys = ref<string[]>([]);
const expandedGroupCount = computed(() => expandedGroupKeys.value.length);
const totalGroupCount = computed(() => groups.value.length);
const canExpandAllGroups = computed(
  () =>
    totalGroupCount.value > 0 &&
    expandedGroupCount.value < totalGroupCount.value,
);
const canCollapseAllGroups = computed(() => expandedGroupCount.value > 0);
const expandedLinkKeys = ref<string[]>([]);
const expandedNoteKeys = ref<string[]>([]);
const expandedUsernameKeys = ref<string[]>([]);
const expandedAssetNameKeys = ref<string[]>([]);
const editOpen = ref(false);
const currentRow = ref<DashboardCloudAssetItem | null>(null);
const detailOpen = ref(false);
const detailLoading = ref(false);
const detailRow = ref<DashboardCloudAssetDetail | null>(null);
const expandedLifecycleRows = ref<Record<string, boolean>>({});
const columnView = ref<'cloud' | 'ip' | 'ops'>('ip');
const formState = reactive({
  actual_expires_at: null as any,
  is_active: true,
  note: '',
  price: '',
  public_ip: '',
  sort_order: 99,
  telegram_group_id: undefined as number | undefined,
  telegram_group_query: '',
  user_query: '',
});
let countdownTimer: null | ReturnType<typeof setInterval> = null;
let syncHighlightTimer: null | ReturnType<typeof setTimeout> = null;
let loadSequence = 0;
let watchedSyncJobId: null | number = null;
let watchedSyncJobPromise: null | Promise<DashboardCloudAssetSyncJob | null> =
  null;

function normalizeDaysLeft(record: DashboardCloudAssetItem) {
  if (typeof record.days_left !== 'number' || Number.isNaN(record.days_left)) {
    return record.actual_expires_at ? Number.POSITIVE_INFINITY : 0;
  }
  return record.days_left;
}

function normalizeExpiresAt(value: null | string | undefined) {
  if (!value) {
    return Number.POSITIVE_INFINITY;
  }
  const timestamp = dayjs(value).valueOf();
  return Number.isNaN(timestamp) ? Number.POSITIVE_INFINITY : timestamp;
}

function normalizeUpdatedAt(value: null | string | undefined) {
  if (!value) {
    return 0;
  }
  const timestamp = dayjs(value).valueOf();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function compareByDaysLeft(
  a: DashboardCloudAssetItem,
  b: DashboardCloudAssetItem,
) {
  const daysDiff = normalizeDaysLeft(a) - normalizeDaysLeft(b);
  if (daysDiff !== 0) {
    return daysDiff;
  }
  const expiresDiff =
    normalizeExpiresAt(a.actual_expires_at) -
    normalizeExpiresAt(b.actual_expires_at);
  if (expiresDiff !== 0) {
    return expiresDiff;
  }
  return normalizeUpdatedAt(b.updated_at) - normalizeUpdatedAt(a.updated_at);
}

type CloudAssetTableRecord = Partial<DashboardCloudAssetItem> &
  Record<string, any>;

function isUnattachedIpAsset(record: CloudAssetTableRecord) {
  const providerResourceId = String(record.provider_resource_id || '');
  const assetName = String(record.asset_name || '').trim();
  const instanceId = String(record.instance_id || '').trim();
  return (
    record.is_unattached_ip === true ||
    record.resource_kind === 'unattached_ip' ||
    !record.public_ip ||
    providerResourceId.includes('StaticIp/') ||
    providerResourceId.includes(':StaticIp/') ||
    (assetName.startsWith('StaticIp-') && !instanceId) ||
    (record.provider_status || '').includes('固定IP保留中') ||
    (record.provider_status || '').includes('固定 IP 保留中') ||
    (record.provider_status || '').includes('未附加固定IP') ||
    (record.provider_status || '').includes('未附加IP')
  );
}

function isDeletedAsset(record: DashboardCloudAssetItem) {
  if (isUnattachedIpAsset(record)) {
    return false;
  }
  return (
    !record.is_active ||
    [
      'deleted',
      'deleting',
      'expired',
      'terminated',
      'terminating',
      'unknown',
    ].includes(record.status) ||
    ['删除中', '已删除', '已终止', '已过期', '未知状态', '终止中'].includes(
      record.status_label || '',
    )
  );
}

const displayedItems = computed(() =>
  showDeletedAssets.value || riskStatus.value !== 'all'
    ? items.value
    : items.value.filter((item) => !isDeletedAsset(item)),
);
const deletedAssetCount = computed(() =>
  Number(
    riskCounts.value.deleted ??
      items.value.filter((item) => isDeletedAsset(item)).length,
  ),
);

function assetDisplayRank(record: DashboardCloudAssetItem) {
  return Number(record.risk_rank ?? 20);
}

function compareByDisplayOrder(
  a: DashboardCloudAssetItem,
  b: DashboardCloudAssetItem,
) {
  const rankDiff = assetDisplayRank(a) - assetDisplayRank(b);
  if (rankDiff !== 0) {
    return rankDiff;
  }
  const daysDiff = compareByDaysLeft(a, b);
  if (daysDiff !== 0) {
    return daysDiff;
  }
  return (b.sort_order || 99) - (a.sort_order || 99);
}

function sortAssets(
  records: DashboardCloudAssetItem[],
  preserveBackendOrder = false,
) {
  if (preserveBackendOrder || totalSortMode.value !== 'default') {
    return [...records];
  }
  return [...records].toSorted(compareByDisplayOrder);
}

function totalSortParams() {
  if (totalSortMode.value === 'expires_asc') {
    return {
      sort_by: 'actual_expires_at' as const,
      sort_order: 'asc' as const,
    };
  }
  if (totalSortMode.value === 'expires_desc') {
    return {
      sort_by: 'actual_expires_at' as const,
      sort_order: 'desc' as const,
    };
  }
  if (totalSortMode.value === 'remaining_asc') {
    return { sort_by: 'days_left' as const, sort_order: 'asc' as const };
  }
  if (totalSortMode.value === 'remaining_desc') {
    return { sort_by: 'days_left' as const, sort_order: 'desc' as const };
  }
  return {};
}

function activeAssetCount(records: DashboardCloudAssetItem[]) {
  return records.filter(
    (item) =>
      item.is_active &&
      !isDeletedAsset(item) &&
      !['deleted', 'deleting', 'terminated', 'terminating'].includes(
        item.status,
      ),
  ).length;
}

function userGroupTitle(item: DashboardCloudAssetItem) {
  return item.user_display_name || '未绑定用户';
}

function userGroupLabel(item: DashboardCloudAssetItem) {
  const usernameLabel = usernamePipeLabel(item);
  return usernameLabel === '-'
    ? String(item.tg_user_id || item.user_id || '-')
    : usernameLabel;
}

function userGroupId(item: DashboardCloudAssetItem) {
  return item.user_id || item.tg_user_id || null;
}

function telegramGroupTitle(item: DashboardCloudAssetItem) {
  if (!item.telegram_group_id) return '未绑定群组';
  return (
    item.telegram_group_title ||
    String(item.telegram_group_chat_id || item.telegram_group_id)
  );
}

function telegramGroupLabel(item: DashboardCloudAssetItem) {
  if (!item.telegram_group_id) return '-';
  return item.telegram_group_username
    ? `@${item.telegram_group_username}`
    : String(item.telegram_group_chat_id || '-');
}

function buildAssetGroups(
  records: DashboardCloudAssetItem[],
  preserveBackendOrder = false,
) {
  const groupMap = new Map<string, DashboardCloudAssetGroup>();
  for (const item of sortAssets(records, preserveBackendOrder)) {
    const fallbackUserId = userGroupId(item);
    const useUserGroup = groupMode.value === 'user' || !item.telegram_group_id;
    const groupKey = useUserGroup
      ? `user:${fallbackUserId || 'unbound'}`
      : `group:${item.telegram_group_id}`;
    const group = groupMap.get(groupKey) || {
      default_expanded: true,
      items: [],
      telegram_group_chat_id: useUserGroup
        ? undefined
        : item.telegram_group_chat_id,
      telegram_group_id: useUserGroup ? undefined : item.telegram_group_id,
      telegram_group_title: useUserGroup ? undefined : telegramGroupTitle(item),
      telegram_group_username: useUserGroup
        ? undefined
        : item.telegram_group_username,
      tg_user_id: useUserGroup ? fallbackUserId : null,
      user_display_name: useUserGroup
        ? userGroupTitle(item)
        : telegramGroupTitle(item),
      user_key: groupKey,
      username_label: useUserGroup
        ? userGroupLabel(item)
        : telegramGroupLabel(item),
    };
    group.items.push(item);
    groupMap.set(groupKey, group);
  }
  if (preserveBackendOrder || totalSortMode.value !== 'default') {
    return [...groupMap.values()];
  }
  return [...groupMap.values()].toSorted((a, b) => {
    const aExpires = Math.min(
      ...a.items.map((item) => normalizeExpiresAt(item.actual_expires_at)),
    );
    const bExpires = Math.min(
      ...b.items.map((item) => normalizeExpiresAt(item.actual_expires_at)),
    );
    if (aExpires !== bExpires) return aExpires - bExpires;
    return String(
      a.user_display_name || a.telegram_group_title || '未绑定',
    ).localeCompare(
      String(b.user_display_name || b.telegram_group_title || '未绑定'),
    );
  });
}

function refreshGroupedItems(
  records: DashboardCloudAssetItem[],
  resetExpanded = false,
  preserveBackendOrder = false,
) {
  applyGroupedPage(
    buildAssetGroups(records, preserveBackendOrder),
    resetExpanded,
  );
}

function applyGroupedPage(
  nextGroups: DashboardCloudAssetGroup[],
  resetExpanded = false,
) {
  const previousGroupKeys = new Set(
    groups.value.map((group) => group.user_key),
  );
  const previousExpandedKeys = new Set(expandedGroupKeys.value);

  groups.value = nextGroups;
  expandedGroupKeys.value = nextGroups
    .filter((group) => {
      if (group.default_expanded === false) return false;
      if (resetExpanded || previousGroupKeys.size === 0) return true;
      return (
        previousExpandedKeys.has(group.user_key) ||
        !previousGroupKeys.has(group.user_key)
      );
    })
    .map((group) => group.user_key);
}

function setAllGroupsExpanded(expanded: boolean) {
  expandedGroupKeys.value = expanded
    ? groups.value.map((group) => group.user_key)
    : [];
}

function resetListPages() {
  groupPagination.page = 1;
  assetPagination.page = 1;
}

function handleDeletedAssetsVisibleChange() {
  resetListPages();
  clearSelectedRows();
  loadData();
}

function handleGroupPageChange(page: number, pageSize: number) {
  const nextPageSize = Number(pageSize || groupPagination.pageSize);
  const pageSizeChanged = nextPageSize !== groupPagination.pageSize;
  groupPagination.page = pageSizeChanged ? 1 : Number(page || 1);
  groupPagination.pageSize = nextPageSize;
  loadData();
}

function handleExpandedGroupKeysChange(
  activeKeys: Array<number | string> | number | string,
) {
  expandedGroupKeys.value = Array.isArray(activeKeys)
    ? activeKeys.map(String)
    : (activeKeys
      ? [String(activeKeys)]
      : []);
}

function regionDisplay(record: DashboardCloudAssetItem) {
  return record.region_label || record.region_name || record.region_code || '-';
}

function hasAssetPrice(record: DashboardCloudAssetItem) {
  const price = Number(record.price || 0);
  return Number.isFinite(price) && price > 0;
}

function assetPriceLabel(record: DashboardCloudAssetItem) {
  if (!hasAssetPrice(record)) {
    return '未设置';
  }
  return `${record.price} ${record.currency || 'USDT'}`;
}

function empty(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function formatNetworkBytes(value?: null | number) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return '-';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const amount = bytes / 1024 ** unitIndex;
  return `${amount >= 100 || unitIndex === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[unitIndex]}`;
}

function canRunNetworkCheck(record: DashboardCloudAssetItem) {
  return Boolean(
    !record.is_unattached_ip &&
    record.provider &&
    (record.instance_id || record.provider_resource_id || record.asset_name) &&
    !['deleted', 'terminated'].includes(record.status),
  );
}

function networkSpeedColor(record: DashboardCloudAssetItem) {
  const stats = record.network_stats;
  if (!stats || stats.speed_status === 'not_run') return 'default';
  if (stats.speed_status === 'failed') return 'error';
  const latency = Number(stats.latency_ms || 0);
  if (latency > 250) return 'error';
  if (latency > 100) return 'warning';
  return 'success';
}

function networkSpeedLabel(record: DashboardCloudAssetItem) {
  const stats = record.network_stats;
  if (!stats || stats.speed_status === 'not_run') return '未测速';
  if (stats.speed_status === 'failed') return '测速失败';
  return `延迟 ${stats.latency_ms || '-'} ms`;
}

function networkTrafficLabel(record: DashboardCloudAssetItem) {
  const stats = record.network_stats;
  if (!stats || stats.traffic_status === 'not_run') return '未统计流量';
  if (stats.traffic_status === 'failed') return '流量刷新失败';
  if (stats.traffic_source === 'aliyun_traffic_package') {
    const used = stats.traffic_used_bytes ?? stats.traffic_out_bytes;
    return `本月出 ${formatNetworkBytes(used)} / ${formatNetworkBytes(stats.traffic_quota_bytes)}`;
  }
  return `本月入 ${formatNetworkBytes(stats.traffic_in_bytes)} / 出 ${formatNetworkBytes(stats.traffic_out_bytes)}`;
}

function networkStatsTime(record: DashboardCloudAssetItem) {
  const stats = record.network_stats;
  const value = stats?.traffic_collected_at || stats?.speed_tested_at;
  return value ? dayjs(value).format('MM-DD HH:mm') : '';
}

function networkStatsError(record: DashboardCloudAssetItem) {
  return [
    record.network_stats?.speed_error,
    record.network_stats?.traffic_error,
  ]
    .filter(Boolean)
    .join('；');
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

function usernamePipeLabel(record: DashboardCloudAssetItem) {
  const value = String(record.username_label || '').trim();
  if (!value || value === '-') {
    return '-';
  }
  return value
    .split(/\s*[/|｜]\s*/)
    .map((item) => item.trim())
    .filter(Boolean)
    .join('｜');
}

function resourceIdLabel(record: DashboardCloudAssetItem) {
  const value = resourceIdValue(record);
  if (!value) {
    return '-';
  }
  return `${resourceIdKindLabel(record)}：${value}`;
}

function resourceIdCopyValue(record: DashboardCloudAssetItem) {
  return resourceIdValue(record);
}

function resourceKindColor(record: CloudAssetTableRecord) {
  if (isUnattachedIpAsset(record)) return 'orange';
  if (record.kind === 'mtproxy') return 'purple';
  return 'blue';
}

function resourceKindLabel(record: CloudAssetTableRecord) {
  if (isUnattachedIpAsset(record)) return '未附加IP';
  return (
    record.resource_kind_label ||
    (record.kind === 'mtproxy' ? 'MTProxy' : '服务器')
  );
}

function resourceIdKindLabel(record: CloudAssetTableRecord) {
  return isUnattachedIpAsset(record) ? '固定IP' : '实例ID';
}

function resourceIdValue(record: CloudAssetTableRecord) {
  if (isUnattachedIpAsset(record)) {
    const providerResourceId = String(record.provider_resource_id || '').trim();
    const staticIpFromResource =
      providerResourceId.includes('StaticIp/') ||
      providerResourceId.includes(':StaticIp/')
        ? providerResourceId.split('/').pop() || ''
        : '';
    const staticIpNameFromAssetName = record.instance_id
      ? ''
      : record.asset_name || '';
    return (
      record.static_ip_name ||
      staticIpFromResource ||
      staticIpNameFromAssetName ||
      record.public_ip ||
      record.previous_public_ip ||
      ''
    );
  }
  return record.instance_id || record.provider_resource_id || '';
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
  return detailRow.value?.lifecycle_order_links?.[value] || '';
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

const detailHistoryOrders = computed<DashboardCloudOrderSummaryItem[]>(
  () => detailRow.value?.history_orders || [],
);

const detailLifecycleRows = computed(() => {
  const rows: Array<Record<string, string>> = [];
  for (const item of detailRow.value?.ip_logs || []) {
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

function riskCountLabel(status: string) {
  return Number(riskCounts.value[status] || 0);
}

function buildProxyLinkItems(record: DashboardCloudAssetItem) {
  const links = [
    record.mtproxy_link,
    ...(record.proxy_links || []).map((item) => item.url),
  ]
    .filter(Boolean)
    .map((value) => String(value).trim())
    .filter(Boolean);
  return [...new Set(links)];
}

function buildProxyLinkText(record: DashboardCloudAssetItem) {
  return buildProxyLinkItems(record).join('\n');
}

async function copyText(text: string, successMessage: string) {
  if (!text) {
    message.warning('没有可复制的内容');
    return;
  }
  await navigator.clipboard.writeText(text);
  message.success(successMessage);
}

async function copyProxyLinks(record: DashboardCloudAssetItem) {
  await copyText(
    buildProxyLinkText(record),
    `已复制 ${record.public_ip || record.asset_name || `#${record.id}`} 的代理链接`,
  );
}

async function copySelectedProxyLinks() {
  const text = selectedAssets.value
    .map((item) => buildProxyLinkText(item))
    .filter(Boolean)
    .join('\n\n');
  await copyText(text, '已复制选中代理的链接');
}

function exportSelectedAssetsCsv() {
  const rows =
    selectedAssets.value.length > 0
      ? selectedAssets.value
      : displayedItems.value;
  if (rows.length === 0) {
    message.warning('没有可导出的代理');
    return;
  }
  const headers = [
    'id',
    'user',
    'username',
    'asset_name',
    'public_ip',
    'expires_at',
    'link',
  ];
  const lines = [
    headers.join(','),
    ...rows.map((item) =>
      [
        item.id,
        JSON.stringify(item.user_display_name || ''),
        JSON.stringify(item.username_label || ''),
        JSON.stringify(item.asset_name || ''),
        JSON.stringify(item.public_ip || ''),
        JSON.stringify(item.actual_expires_at || ''),
        JSON.stringify(buildProxyLinkText(item)),
      ].join(','),
    ),
  ];
  const blob = new Blob([lines.join('\n')], {
    type: 'text/csv;charset=utf-8;',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `cloud-assets-${dayjs().format('YYYYMMDD-HHmmss')}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function clearSelectedRows() {
  selectedRowKeys.value = [];
}

const selectedAssets = computed(() =>
  items.value.filter((item) => selectedRowKeys.value.includes(item.id)),
);

const rowSelection = computed(() => ({
  preserveSelectedRowKeys: true,
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: Array<number | string>) => {
    selectedRowKeys.value = keys
      .map(Number)
      .filter((value) => Number.isFinite(value));
  },
}));

const assetRowSelection = computed(() =>
  columnView.value === 'ip' ? undefined : rowSelection.value,
);

function hasRiskCountBreakdown(counts?: Record<string, number>) {
  if (!counts || Number(counts.all || 0) <= 0) {
    return false;
  }
  return Object.keys(counts).some((key) => key !== 'all');
}

async function refreshGlobalRiskCounts(keywordText: string) {
  const summary = await getDashboardCloudAssetRiskSummaryApi({
    keyword: keywordText,
  });
  riskCounts.value = summary.risk_counts || { all: 0 };
}

const riskFilterOptions = computed(() => [
  { label: `全部 (${riskCounts.value.all || 0})`, value: 'all' },
  { label: `运行中 (${riskCountLabel('normal')})`, value: 'normal' },
  { label: `即将到期 (${riskCountLabel('due_soon')})`, value: 'due_soon' },
  { label: `已过期 (${riskCountLabel('expired')})`, value: 'expired' },
  {
    label: `未附加固定IP (${riskCountLabel('unattached_ip')})`,
    value: 'unattached_ip',
  },
  { label: `异常/待确认 (${riskCountLabel('abnormal')})`, value: 'abnormal' },
  {
    label: `云账号异常 (${riskCountLabel('account_disabled')})`,
    value: 'account_disabled',
  },
  {
    label: `关机计划关闭 (${riskCountLabel('shutdown_disabled')})`,
    value: 'shutdown_disabled',
  },
  {
    label: `未绑定用户 (${riskCountLabel('unbound_user')})`,
    value: 'unbound_user',
  },
  {
    label: `未绑定群组 (${riskCountLabel('unbound_group')})`,
    value: 'unbound_group',
  },
  {
    label: `续费关闭 (${riskCountLabel('auto_renew_off')})`,
    value: 'auto_renew_off',
  },
]);

const columns = [
  {
    title: '归属用户',
    dataIndex: 'cloud_user_summary',
    key: 'cloud_user_summary',
    width: 220,
  },
  {
    title: 'IP用户',
    dataIndex: 'ip_user_summary',
    key: 'ip_user_summary',
    width: 170,
  },
  {
    title: '分组',
    dataIndex: 'telegram_group_summary',
    key: 'telegram_group_summary',
    width: 180,
  },
  {
    title: '用户昵称',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 150,
  },
  {
    title: '用户名',
    dataIndex: 'username_label',
    key: 'username_label',
    width: 180,
  },
  {
    title: '资源信息',
    dataIndex: 'cloud_resource_summary',
    key: 'cloud_resource_summary',
    width: 360,
  },
  { title: '实例名称', dataIndex: 'asset_name', key: 'asset_name', width: 150 },
  {
    title: '云厂商',
    dataIndex: 'provider_label',
    key: 'provider_label',
    width: 120,
  },
  {
    title: '实例ID',
    dataIndex: 'instance_id',
    key: 'instance_id',
    width: 220,
  },
  {
    title: '排序',
    dataIndex: 'sort_order',
    key: 'sort_order',
    width: 90,
    sorter: (a: DashboardCloudAssetItem, b: DashboardCloudAssetItem) =>
      (b.sort_order || 99) - (a.sort_order || 99),
  },
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 120 },
  {
    title: 'IP / 价格',
    dataIndex: 'cloud_ip_price',
    key: 'cloud_ip_price',
    width: 170,
  },
  { title: '公网IP', dataIndex: 'public_ip', key: 'public_ip', width: 140 },
  { title: '价格', dataIndex: 'price', key: 'price', width: 130 },
  {
    title: '代理链接',
    dataIndex: 'mtproxy_link',
    key: 'mtproxy_link',
    width: 320,
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
  {
    title: '云上状态',
    dataIndex: 'provider_status',
    key: 'provider_status',
    width: 150,
  },
  {
    title: '剩余天数',
    dataIndex: 'status_countdown',
    key: 'status_countdown',
    sorter: true,
    width: 140,
  },
  {
    title: '到期时间',
    dataIndex: 'actual_expires_at',
    key: 'actual_expires_at',
    sorter: true,
    width: 130,
  },
  {
    title: '到期/剩余',
    dataIndex: 'ip_expiry_summary',
    key: 'ip_expiry_summary',
    sorter: true,
    width: 170,
  },
  { title: '备注', dataIndex: 'note', key: 'note', width: 150 },
  {
    title: '自动续费',
    dataIndex: 'auto_renew_enabled',
    key: 'auto_renew_enabled',
    width: 130,
  },
  {
    title: '测速 / 本月流量',
    dataIndex: 'network_stats',
    key: 'network_stats',
    width: 260,
  },
  { title: '操作', key: 'actions', fixed: 'right' as const, width: 210 },
  { title: '编辑', key: 'ip_actions', fixed: 'right' as const, width: 90 },
];

const columnViewOptions = [
  { label: '操作视图', value: 'ops' },
  { label: '云资源视图', value: 'cloud' },
  { label: 'IP视图', value: 'ip' },
];
const displayModeOptions = [
  { label: '按群组分组', value: 'telegram_group' },
  { label: '按用户分组', value: 'user' },
  { label: '不分组', value: 'flat' },
];
const assetDisplayMode = computed<AssetDisplayMode>({
  get() {
    return grouped.value ? groupMode.value : 'flat';
  },
  set(value = 'telegram_group') {
    grouped.value = value !== 'flat';
    if (value !== 'flat') {
      groupMode.value = value;
    }
    resetListPages();
    clearSelectedRows();
    if (!grouped.value) {
      groups.value = [];
      expandedGroupKeys.value = [];
    }
    loadData();
  },
});

const assetColumnVisible = reactive<Record<string, boolean>>({});
const assetColumnSwitchOptions = [
  { key: 'cloud_user_summary', label: '归属用户' },
  { key: 'ip_user_summary', label: 'IP用户' },
  { key: 'telegram_group_summary', label: '分组' },
  { key: 'user_display_name', label: '用户昵称' },
  { key: 'username_label', label: '用户名' },
  { key: 'cloud_resource_summary', label: '资源信息' },
  { key: 'asset_name', label: '实例名称' },
  { key: 'provider_label', label: '云厂商' },
  { key: 'instance_id', label: '实例ID' },
  { key: 'sort_order', label: '排序' },
  { key: 'region_label', label: '地区' },
  { key: 'cloud_ip_price', label: 'IP/价格' },
  { key: 'public_ip', label: '公网IP' },
  { key: 'price', label: '价格' },
  { key: 'mtproxy_link', label: '代理链接' },
  { key: 'status', label: '状态' },
  { key: 'provider_status', label: '云上状态' },
  { key: 'status_countdown', label: '剩余天数' },
  { key: 'actual_expires_at', label: '到期时间' },
  { key: 'ip_expiry_summary', label: '到期/剩余' },
  { key: 'note', label: '备注' },
  { key: 'auto_renew_enabled', label: '自动续费' },
  { key: 'network_stats', label: '测速/流量' },
  { key: 'actions', label: '操作' },
  { key: 'ip_actions', label: '编辑' },
] as const;

assetColumnSwitchOptions.forEach((item) => {
  assetColumnVisible[item.key] = ![
    'asset_name',
    'instance_id',
    'network_stats',
  ].includes(item.key);
});

const syncScopeOptions = [
  { label: '同步全部', value: 'all' },
  { label: '只同步AWS', value: 'aws' },
  { label: '只同步阿里云', value: 'aliyun' },
  { label: '同步选中', value: 'selected' },
];

function tableColumnSortOrder(key: string): 'ascend' | 'descend' | undefined {
  if (key === 'actual_expires_at') {
    if (totalSortMode.value === 'expires_asc') return 'ascend';
    if (totalSortMode.value === 'expires_desc') return 'descend';
  }
  if (key === 'status_countdown') {
    if (totalSortMode.value === 'remaining_asc') return 'ascend';
    if (totalSortMode.value === 'remaining_desc') return 'descend';
  }
  return undefined;
}

const assetTableBaseColumns = computed<
  TableColumnsType<DashboardCloudAssetItem>
>(() => {
  const mappedColumns = columns.map((column) => ({
    ...column,
    sortOrder: tableColumnSortOrder(column.key),
  }));
  const filteredByView = mappedColumns.filter((column) => {
    if (columnView.value === 'ip') {
      return [
        'asset_name',
        'auto_renew_enabled',
        'cloud_ip_price',
        'instance_id',
        'ip_actions',
        'ip_expiry_summary',
        'ip_user_summary',
        'network_stats',
        'note',
        'status',
        'telegram_group_summary',
      ].includes(column.key);
    }
    if (columnView.value === 'cloud') {
      return [
        'actions',
        'actual_expires_at',
        'auto_renew_enabled',
        'cloud_ip_price',
        'cloud_resource_summary',
        'cloud_user_summary',
        'network_stats',
        'note',
        'provider_status',
        'status',
        'status_countdown',
        'telegram_group_summary',
      ].includes(column.key);
    }
    if (column.key === 'ip_user_summary') {
      return false;
    }
    if (
      grouped.value &&
      groupMode.value === 'telegram_group' &&
      ['user_display_name', 'username_label'].includes(column.key)
    ) {
      return false;
    }
    return true;
  });
  return filteredByView;
});

const assetColumnSwitches = computed(() => {
  const seen = new Set<string>();
  const keys = new Set(
    assetTableBaseColumns.value
      .map((column) => String(column.key || ''))
      .filter((key) => {
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      }),
  );
  return assetColumnSwitchOptions.filter((item) => keys.has(item.key));
});

const assetTableColumns = computed<TableColumnsType<DashboardCloudAssetItem>>(
  () =>
    assetTableBaseColumns.value.filter(
      (column) => assetColumnVisible[String(column.key || '')] !== false,
    ),
);

const assetTableScroll = computed(() => {
  let width = 80;
  for (const column of assetTableColumns.value) {
    const rawWidth = column.width;
    if (typeof rawWidth === 'number') {
      width += rawWidth;
      continue;
    }
    const parsed = Number.parseInt(String(rawWidth || ''), 10);
    width += Number.isFinite(parsed) ? parsed : 120;
  }
  return { x: Math.max(width, columnView.value === 'ip' ? 1280 : 1800) };
});

const syncJobTableColumns = computed<
  TableColumnsType<DashboardCloudAssetSyncJob>
>(() => [
  { dataIndex: 'id', key: 'id', title: '任务', width: 110 },
  { dataIndex: 'status', key: 'status', title: '状态', width: 130 },
  { dataIndex: 'scope', key: 'scope', title: '范围', width: 260 },
  { dataIndex: 'progress', key: 'progress', title: '进度', width: 140 },
  {
    dataIndex: 'created_at',
    key: 'created_at',
    title: '时间/Worker',
    width: 240,
  },
  { dataIndex: 'errors', key: 'errors', title: '结果', width: 260 },
  { key: 'actions', title: '操作', width: 160 },
]);

type SyncJobTableRecord = Partial<DashboardCloudAssetSyncJob> &
  Record<string, any>;

const syncJobStatusFilterOptions = [
  { label: '全部任务', value: 'all' },
  { label: '活动中', value: 'active' },
  { label: '排队中', value: 'queued' },
  { label: '运行中', value: 'running' },
  { label: '已完成', value: 'succeeded' },
  { label: '部分完成', value: 'partial' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
  { label: '终态', value: 'terminal' },
];

function syncJobStatusColor(status?: string) {
  if (status === 'succeeded') return 'green';
  if (status === 'failed') return 'red';
  if (status === 'partial') return 'orange';
  if (status === 'running') return 'processing';
  if (status === 'cancelled') return 'default';
  if (status === 'queued') return 'blue';
  return 'default';
}

function syncJobEventColor(eventType?: string) {
  if (eventType === 'error') return 'red';
  if (eventType === 'warning' || eventType === 'cancel') return 'orange';
  if (eventType === 'progress' || eventType === 'task') return 'blue';
  if (eventType === 'claimed' || eventType === 'heartbeat') return 'cyan';
  if (eventType === 'retry') return 'purple';
  return 'default';
}

function syncJobScopeLabel(job: SyncJobTableRecord) {
  const scope = job.scope || {};
  const providerItems = Array.isArray(job.providers)
    ? job.providers
    : (Array.isArray(scope.providers)
      ? scope.providers
      : []);
  const providers = providerItems.join(' / ') || 'all';
  const assets = job.asset_ids?.length ? `${job.asset_ids.length} 条代理` : '';
  const accounts = job.account_ids?.length
    ? `${job.account_ids.length} 个账号`
    : '';
  const regions = [scope.aliyun_region, scope.aws_region]
    .filter(Boolean)
    .join(' / ');
  return [providers, assets, accounts, regions].filter(Boolean).join(' · ');
}

function syncJobResultLabel(job: SyncJobTableRecord) {
  const errors = job.errors || job.result?.errors || [];
  const warnings = job.warnings || job.result?.warnings || [];
  if (errors.length > 0) return errors.slice(0, 2).join('；');
  if (warnings.length > 0) return warnings.slice(0, 2).join('；');
  if (job.cancelled || job.status === 'cancelled') return '已取消';
  if (job.is_terminal) return '完成';
  return job.current_task || '等待执行';
}

function syncJobWorkerLabel(job: SyncJobTableRecord) {
  const worker = job.worker_id || job.scope?.worker_id || '';
  const heartbeat = job.worker_heartbeat_at
    ? formatTime(job.worker_heartbeat_at)
    : '-';
  if (!worker && heartbeat === '-') return 'worker: -';
  return `${worker || 'worker'} · ${heartbeat}`;
}

function syncJobEventSummary(event: DashboardCloudAssetSyncJobEvent) {
  if (event.message) return event.message;
  if (event.event_type_label) return event.event_type_label;
  return event.event_type;
}

function formatSyncMetricSeconds(seconds?: number) {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) return '-';
  if (value >= 3600) return `${(value / 3600).toFixed(1)}h`;
  if (value >= 60) return `${(value / 60).toFixed(1)}m`;
  return `${Math.round(value)}s`;
}

function formatSyncFailureRate(value?: number) {
  const rate = Number(value || 0);
  if (!Number.isFinite(rate) || rate <= 0) return '0%';
  return `${(rate * 100).toFixed(1)}%`;
}

function isSyncJobRetrying(jobId?: number | string) {
  const parsedId = Number(jobId || 0);
  return parsedId > 0 && syncJobRetryingIds.value.includes(parsedId);
}

function isSyncJobCancelling(jobId?: number | string) {
  const parsedId = Number(jobId || 0);
  return parsedId > 0 && syncJobCancellingIds.value.includes(parsedId);
}

function compactJson(value: unknown) {
  if (
    !value ||
    (typeof value === 'object' && Object.keys(value).length === 0)
  ) {
    return '';
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function handleAssetTableChange(
  pagination: any,
  _filters: unknown,
  sorter: any,
) {
  const nextPage = Number(pagination?.current || assetPagination.page || 1);
  const nextPageSize = Number(
    pagination?.pageSize || assetPagination.pageSize || ASSET_PAGE_SIZE,
  );
  const pageChanged =
    !grouped.value &&
    (nextPage !== assetPagination.page ||
      nextPageSize !== assetPagination.pageSize);
  if (!grouped.value) {
    assetPagination.page =
      nextPageSize === assetPagination.pageSize ? nextPage : 1;
    assetPagination.pageSize = nextPageSize;
  }

  const activeSorter = Array.isArray(sorter)
    ? sorter.find((item) => item.order)
    : sorter;
  const key = activeSorter?.columnKey || activeSorter?.field;
  const order = activeSorter?.order;
  if (!['actual_expires_at', 'status_countdown'].includes(key)) {
    if (pageChanged) {
      loadData();
    }
    return;
  }
  const previousSortMode = totalSortMode.value;
  if (!order) {
    totalSortMode.value = 'default';
  } else if (key === 'actual_expires_at') {
    totalSortMode.value = order === 'ascend' ? 'expires_asc' : 'expires_desc';
  } else if (key === 'status_countdown') {
    totalSortMode.value =
      order === 'ascend' ? 'remaining_asc' : 'remaining_desc';
  }
  const sortChanged = previousSortMode !== totalSortMode.value;
  if (sortChanged) {
    resetListPages();
  }
  if (pageChanged || sortChanged) {
    loadData();
  }
}

function groupUserSummary(group: DashboardCloudAssetGroup) {
  if (!group.telegram_group_id) return '';
  const labels = group.items
    .map((item) => {
      if (item.user_display_name && item.user_display_name !== '未绑定用户') {
        return item.user_display_name;
      }
      const usernameLabel = usernamePipeLabel(item);
      if (usernameLabel && usernameLabel !== '-') {
        return usernameLabel;
      }
      if (item.tg_user_id) return `TG ${item.tg_user_id}`;
      if (item.user_id) return `用户 ${item.user_id}`;
      return '';
    })
    .filter(Boolean);
  const uniqueLabels = [...new Set(labels)];
  if (uniqueLabels.length === 0) return '未绑定用户';
  if (uniqueLabels.length <= 2) return uniqueLabels.join('、');
  return `${uniqueLabels.slice(0, 2).join('、')} 等 ${uniqueLabels.length} 个用户`;
}

function asDashboardCloudAssetItem(record: Record<string, any>) {
  return record as DashboardCloudAssetItem;
}

async function openDetail(record: DashboardCloudAssetItem) {
  detailOpen.value = true;
  detailLoading.value = true;
  try {
    detailRow.value = await getDashboardCloudAssetDetailApi(record.id);
  } catch (error: any) {
    message.error(error?.message || '加载详情失败');
    detailOpen.value = false;
  } finally {
    detailLoading.value = false;
  }
}

function openDetailPage(assetId?: number) {
  if (!assetId) return;
  router.push(`/admin/cloud-assets/${assetId}`).catch(() => {});
}

function openOrder(path?: null | string) {
  if (!path) return;
  router.push(path).catch(() => {});
}

function formatRefreshTime(value: dayjs.Dayjs | null) {
  return value ? value.format('MM-DD HH:mm:ss') : '-';
}

function normalizedIntervalSeconds(value: number | undefined) {
  const seconds = Number(value || DEFAULT_AUTO_REFRESH_SECONDS);
  return Number.isFinite(seconds) && seconds >= 60
    ? Math.floor(seconds)
    : DEFAULT_AUTO_REFRESH_SECONDS;
}

function formatDuration(seconds: number) {
  if (seconds % 3600 === 0) {
    return `${seconds / 3600}小时`;
  }
  if (seconds % 60 === 0) {
    return `${seconds / 60}分钟`;
  }
  return `${seconds}秒`;
}

function resetRefreshCountdown() {
  nextRefreshInSeconds.value = autoSyncEverySeconds.value;
}

function markRecentSync() {
  recentSyncHighlight.value = true;
  if (syncHighlightTimer) {
    clearTimeout(syncHighlightTimer);
  }
  syncHighlightTimer = setTimeout(() => {
    recentSyncHighlight.value = false;
    syncHighlightTimer = null;
  }, 10_000);
}

function delay(milliseconds: number) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function applySyncJobSummary(job: DashboardCloudAssetSyncJob | null) {
  const result = job?.result || {};
  lastSyncTasks.value = result.tasks || job?.tasks || [];
  lastSkippedSyncTasks.value = result.skipped_tasks || job?.skipped_tasks || [];
}

function upsertSyncJobStatus(job: DashboardCloudAssetSyncJob | null) {
  if (!job?.id) return;
  const index = syncJobs.value.findIndex((item) => item.id === job.id);
  if (index !== -1) {
    syncJobs.value = [
      ...syncJobs.value.slice(0, index),
      job,
      ...syncJobs.value.slice(index + 1),
    ];
    return;
  }
  if (syncJobsPagination.page === 1) {
    syncJobs.value = [job, ...syncJobs.value].slice(
      0,
      syncJobsPagination.pageSize,
    );
    syncJobsPagination.total += 1;
  }
}

async function pollCloudAssetSyncJob(jobId: number) {
  for (let attempt = 0; attempt < 900; attempt += 1) {
    const job = await getDashboardCloudAssetSyncJobApi(jobId);
    activeSyncJob.value = job;
    upsertSyncJobStatus(job);
    if (
      job.is_terminal ||
      ['failed', 'partial', 'succeeded'].includes(job.status)
    ) {
      applySyncJobSummary(job);
      return job;
    }
    await delay(2000);
  }
  throw new Error('同步任务等待超时，请稍后刷新查看结果');
}

function monitorCloudAssetSyncJob(jobId: number) {
  if (watchedSyncJobId === jobId && watchedSyncJobPromise) {
    return watchedSyncJobPromise;
  }
  watchedSyncJobId = jobId;
  watchedSyncJobPromise = pollCloudAssetSyncJob(jobId).finally(() => {
    if (watchedSyncJobId === jobId) {
      watchedSyncJobId = null;
      watchedSyncJobPromise = null;
    }
  });
  return watchedSyncJobPromise;
}

function resumeCloudAssetSyncJob(job: DashboardCloudAssetSyncJob) {
  if (watchedSyncJobId === job.id) return;
  activeSyncJob.value = job;
  void monitorCloudAssetSyncJob(job.id)
    .then(async (completedJob) => {
      if (!completedJob) return;
      activeSyncJob.value = null;
      markRecentSync();
      await loadData();
    })
    .catch((error: any) => {
      logCloudSyncConsole('resume-job-error', error, true);
      message.error(error?.message || '后台同步任务轮询失败');
    });
}

async function loadSyncJobs(page = syncJobsPagination.page) {
  syncJobsLoading.value = true;
  try {
    const status =
      syncJobsStatusFilter.value === 'all'
        ? undefined
        : syncJobsStatusFilter.value;
    const response = await getDashboardCloudAssetSyncJobsApi({
      failed_only: syncJobsFailedOnly.value ? 1 : undefined,
      page,
      page_size: syncJobsPagination.pageSize,
      status,
    });
    syncJobs.value = response.items || [];
    syncJobsPagination.page = response.page || page;
    syncJobsPagination.pageSize =
      response.page_size || syncJobsPagination.pageSize;
    syncJobsPagination.total = response.total || 0;
  } finally {
    syncJobsLoading.value = false;
  }
}

async function loadSyncJobMetrics() {
  syncJobMetricsLoading.value = true;
  try {
    syncJobMetrics.value = await getDashboardCloudAssetSyncJobMetricsApi();
  } finally {
    syncJobMetricsLoading.value = false;
  }
}

function openSyncJobs() {
  syncJobsOpen.value = true;
  loadSyncJobs(1);
  loadSyncJobMetrics();
}

function handleSyncJobsFilterChange() {
  syncJobsPagination.page = 1;
  loadSyncJobs(1);
}

function openSyncJobDetail(jobId?: number | string) {
  const parsedId = Number(jobId || 0);
  if (!parsedId) return;
  router.push(`/admin/cloud-sync-jobs/${parsedId}`).catch(() => {});
}

function handleSyncJobsTableChange(pagination: any) {
  syncJobsPagination.page = Number(pagination?.current || 1);
  syncJobsPagination.pageSize = Number(
    pagination?.pageSize || syncJobsPagination.pageSize,
  );
  loadSyncJobs(syncJobsPagination.page);
}

async function retrySyncJob(job: SyncJobTableRecord) {
  if (!requireCloudDangerPermission('重试同步任务')) return;
  const jobId = Number(job.id || 0);
  if (!jobId) {
    message.error('同步任务 ID 无效');
    return;
  }
  syncJobRetryingIds.value = [...syncJobRetryingIds.value, jobId];
  try {
    const result = await retryDashboardCloudAssetSyncJobApi(jobId);
    if (result.job_id) {
      message.success('同步任务已重新入队');
      upsertSyncJobStatus(result.job || null);
      await loadSyncJobs(1);
      await loadSyncJobMetrics();
      void monitorCloudAssetSyncJob(result.job_id);
    }
  } catch (error: any) {
    message.error(error?.message || '重试同步任务失败');
  } finally {
    syncJobRetryingIds.value = syncJobRetryingIds.value.filter(
      (id) => id !== jobId,
    );
  }
}

async function cancelSyncJob(job: SyncJobTableRecord) {
  if (!requireCloudDangerPermission('取消同步任务')) return;
  const jobId = Number(job.id || 0);
  if (!jobId) {
    message.error('同步任务 ID 无效');
    return;
  }
  syncJobCancellingIds.value = [...syncJobCancellingIds.value, jobId];
  try {
    const result = await cancelDashboardCloudAssetSyncJobApi(jobId);
    if (result.job) {
      upsertSyncJobStatus(result.job);
    }
    message.success(result.message || '取消请求已提交');
    await loadSyncJobs(syncJobsPagination.page);
    await loadSyncJobMetrics();
  } catch (error: any) {
    message.error(error?.message || '取消同步任务失败');
  } finally {
    syncJobCancellingIds.value = syncJobCancellingIds.value.filter(
      (id) => id !== jobId,
    );
  }
}

function handleRiskStatusChange() {
  resetListPages();
  clearSelectedRows();
  loadData();
}

function setRiskStatus(status: string) {
  if (riskStatus.value === status) {
    return;
  }
  riskStatus.value = status;
  handleRiskStatusChange();
}

function handleColumnViewChange() {
  if (columnView.value === 'ip' && grouped.value) {
    grouped.value = false;
    groups.value = [];
    expandedGroupKeys.value = [];
  }
  resetListPages();
  clearSelectedRows();
  loadData();
}

function applyCloudAssetSyncStatus(
  syncStatus: DashboardCloudAssetsSyncStatus | null | undefined,
) {
  if (!syncStatus) return;
  autoSyncEverySeconds.value = normalizedIntervalSeconds(
    syncStatus.auto_sync_every_seconds,
  );
  resetRefreshCountdown();
  lastSyncedAt.value = syncStatus.last_synced_at
    ? dayjs(syncStatus.last_synced_at)
    : null;
  awsExistingCount.value = syncStatus.aws_existing_count || 0;
  aliyunExistingCount.value = syncStatus.aliyun_existing_count || 0;
  unattachedIpCount.value = syncStatus.unattached_ip_count || 0;
  if (syncStatus.metrics) {
    syncJobMetrics.value = syncStatus.metrics;
  }
  const latestCompletedJob = syncStatus.recent_jobs?.find(
    (job) => job.is_terminal,
  );
  lastSyncTasks.value =
    latestCompletedJob?.tasks || syncStatus.recent_syncs?.[0]?.tasks || [];
  lastSkippedSyncTasks.value =
    latestCompletedJob?.skipped_tasks ||
    syncStatus.recent_syncs?.[0]?.skipped_tasks ||
    [];
  if (!syncJobsOpen.value && syncStatus.recent_jobs?.length) {
    syncJobs.value = syncStatus.recent_jobs;
  }
  const activeJob = syncStatus.active_jobs?.[0];
  if (activeJob) {
    resumeCloudAssetSyncJob(activeJob);
  } else if (!watchedSyncJobId) {
    activeSyncJob.value = null;
  }
}

async function loadData() {
  const sequence = ++loadSequence;
  loading.value = true;
  loadingMore.value = false;
  loadProgress.done = false;
  loadProgress.loaded = 0;
  loadProgress.total = 0;
  loadProgress.pageSize = grouped.value
    ? groupPagination.pageSize
    : assetPagination.pageSize;
  try {
    const keywordText = keyword.value.trim();
    const sortParams = totalSortParams();
    const compactParams =
      columnView.value === 'ip' ? { compact: 1 as const } : {};
    const assetRequest = grouped.value
      ? getDashboardCloudAssetsGroupedPageApi({
          ...compactParams,
          group_by: groupMode.value,
          keyword: keywordText,
          page: groupPagination.page,
          page_size: groupPagination.pageSize,
          risk_status: riskStatus.value,
          show_deleted: showDeletedAssets.value ? 1 : 0,
          ...sortParams,
        })
      : getDashboardCloudAssetsPageApi({
          ...compactParams,
          group_by: groupMode.value,
          keyword: keywordText,
          page: assetPagination.page,
          page_size: assetPagination.pageSize,
          risk_status: riskStatus.value,
          show_deleted: showDeletedAssets.value ? 1 : 0,
          ...sortParams,
        });
    const syncStatusRequest = getDashboardCloudAssetsSyncStatusApi()
      .then((syncStatus) => {
        if (sequence === loadSequence) {
          applyCloudAssetSyncStatus(syncStatus);
        }
        return syncStatus;
      })
      .catch(() => null);
    const firstPage = await assetRequest;
    if (sequence !== loadSequence) return;
    void syncStatusRequest;

    const nextRiskCounts = firstPage.risk_counts || {};
    riskCounts.value = nextRiskCounts;
    if (!hasRiskCountBreakdown(nextRiskCounts)) {
      await refreshGlobalRiskCounts(keywordText);
      if (sequence !== loadSequence) return;
    }

    items.value = firstPage.items || [];
    loadProgress.total = firstPage.total || items.value.length;
    if (grouped.value) {
      const groupedPage = firstPage as DashboardCloudAssetGroupedResponse;
      loadProgress.loaded = groupedPage.groups?.length || 0;
      groupPagination.page = groupedPage.page || groupPagination.page;
      groupPagination.pageSize =
        groupedPage.page_size || groupPagination.pageSize;
      groupPagination.total =
        groupedPage.total || groupedPage.groups?.length || 0;
      loadProgress.total = groupPagination.total;
      applyGroupedPage(groupedPage.groups || [], true);
      return;
    }

    loadProgress.loaded = items.value.length;
    assetPagination.page = firstPage.page || assetPagination.page;
    assetPagination.pageSize = firstPage.page_size || assetPagination.pageSize;
    assetPagination.total = firstPage.total || 0;
    groups.value = [];
    expandedGroupKeys.value = [];
    loadProgress.done = true;
  } finally {
    if (sequence === loadSequence) {
      loading.value = false;
      loadingMore.value = false;
      loadProgress.done = true;
      lastRefreshedAt.value = dayjs();
      resetRefreshCountdown();
    }
  }
}

function handleSearch() {
  resetListPages();
  clearSelectedRows();
  loadData();
}

function resetSearch() {
  keyword.value = '';
  riskStatus.value = 'all';
  clearSelectedRows();
  resetListPages();
  loadData();
}

async function loadTelegramGroups() {
  try {
    telegramGroups.value = await getDashboardTelegramGroupsApi({
      binding_only: true,
    });
  } catch {
    telegramGroups.value = [];
  }
}

function telegramGroupOptions() {
  return telegramGroups.value
    .filter((item) => !item.collapsed)
    .map((item) => ({
      label: `${item.title || item.chat_id}${item.username ? ` (@${item.username})` : ''}`,
      value: item.id,
    }));
}

function handleTelegramGroupSelectChange(value: unknown) {
  if (!value) {
    formState.telegram_group_query = '';
    return;
  }
  const selectedGroup = telegramGroups.value.find(
    (item) => item.id === Number(value),
  );
  if (selectedGroup) {
    formState.telegram_group_query = selectedGroup.chat_id
      ? String(selectedGroup.chat_id)
      : selectedGroup.username || selectedGroup.title || '';
  }
}

function isAssetSyncing(assetId: number) {
  return assetSyncingIds.value.includes(assetId);
}

function isNetworkSpeedTesting(assetId: number) {
  return networkSpeedTestingIds.value.includes(assetId);
}

function isNetworkTrafficLoading(assetId: number) {
  return networkTrafficLoadingIds.value.includes(assetId);
}

async function executeNetworkSpeedTest(record: DashboardCloudAssetItem) {
  networkSpeedTestingIds.value = [...networkSpeedTestingIds.value, record.id];
  try {
    const result = await runDashboardCloudAssetSpeedTestApi(record.id);
    replaceAssetInList(result.asset);
    if (detailRow.value?.id === result.asset.id) {
      detailRow.value = { ...detailRow.value, ...result.asset };
    }
    if (result.ok) {
      message.success(
        `测速完成：${record.public_ip || record.asset_name || `#${record.id}`}`,
      );
    } else {
      message.warning(
        result.asset.network_stats?.speed_error || '测速未成功，请查看网络统计',
      );
    }
  } finally {
    networkSpeedTestingIds.value = networkSpeedTestingIds.value.filter(
      (id) => id !== record.id,
    );
  }
}

function runNetworkSpeedTest(record: DashboardCloudAssetItem) {
  if (!requireCloudDangerPermission('执行服务器测速')) return;
  if (!canRunNetworkCheck(record)) {
    message.warning('当前资源不是可测速的云服务器实例');
    return;
  }
  Modal.confirm({
    title: '执行真实上下行测速',
    content:
      '测速会登录目标服务器并连接 Cloudflare 测速节点，预计下载 200 MB、上传 100 MB，单次约消耗 300 MB 流量，通常需要 15-300 秒。',
    okText: '开始测速',
    cancelText: '取消',
    onOk: () => executeNetworkSpeedTest(record),
  });
}

async function refreshNetworkTraffic(record: DashboardCloudAssetItem) {
  if (!requireCloudDangerPermission('刷新服务器流量')) return;
  if (!canRunNetworkCheck(record)) {
    message.warning('当前资源不是可统计流量的云服务器实例');
    return;
  }
  networkTrafficLoadingIds.value = [
    ...networkTrafficLoadingIds.value,
    record.id,
  ];
  try {
    const result = await refreshDashboardCloudAssetTrafficApi(record.id);
    replaceAssetInList(result.asset);
    if (detailRow.value?.id === result.asset.id) {
      detailRow.value = { ...detailRow.value, ...result.asset };
    }
    if (result.ok) {
      message.success(
        `已刷新 ${record.public_ip || record.asset_name || `#${record.id}`} 的本月流量`,
      );
    } else {
      message.warning(
        result.asset.network_stats?.traffic_error || '本月流量刷新失败',
      );
    }
  } finally {
    networkTrafficLoadingIds.value = networkTrafficLoadingIds.value.filter(
      (id) => id !== record.id,
    );
  }
}

function logCloudSyncConsole(label: string, payload: unknown, isError = false) {
  void label;
  void payload;
  void isError;
}

async function syncAssetStatus(record: DashboardCloudAssetItem) {
  try {
    await syncAssetStatusInternal(record, false);
  } catch {
    // 错误消息已在 syncAssetStatusInternal 内展示。
  }
}

async function syncAssetStatusInternal(
  record: DashboardCloudAssetItem,
  silent = false,
) {
  if (!requireCloudDangerPermission('更新云上状态')) return;
  assetSyncingIds.value = [...assetSyncingIds.value, record.id];
  try {
    logCloudSyncConsole('single-start', {
      asset_id: record.id,
      instance_id: record.instance_id,
      provider: record.provider,
      public_ip: record.public_ip || record.previous_public_ip,
    });
    const result = await syncDashboardCloudAssetStatusApi(record.id);
    logCloudSyncConsole('single-result', result, result?.ok === false);
    if (result?.asset) {
      replaceAssetInList(result.asset);
    }
    if (result?.ok === false || result?.errors?.length) {
      if (!silent) {
        message.warning(
          `已尝试更新 ${record.public_ip || record.asset_name || `#${record.id}`}，但同步返回异常`,
        );
      }
      throw new Error('同步返回异常');
    }
    if (!silent) {
      message.success(
        `已更新 ${record.public_ip || record.asset_name || `#${record.id}`} 的服务器状态`,
      );
    }
  } catch (error: any) {
    logCloudSyncConsole(
      'single-error',
      {
        asset_id: record.id,
        error,
      },
      true,
    );
    if (!silent) {
      message.error(error?.message || '更新状态失败');
    }
    throw error;
  } finally {
    assetSyncingIds.value = assetSyncingIds.value.filter(
      (id) => id !== record.id,
    );
  }
}

async function batchSyncSelectedAssets() {
  if (!requireCloudDangerPermission('批量同步代理')) return;
  if (selectedAssets.value.length === 0) {
    message.warning('请先选择要同步的代理');
    return;
  }
  syncing.value = true;
  try {
    const assetIds = selectedAssets.value.map((asset) => asset.id);
    const selectedCount = assetIds.length;
    logCloudSyncConsole('batch-start', {
      asset_ids: assetIds,
      selected_count: selectedAssets.value.length,
    });
    const queuedResult = await syncDashboardCloudAssetsApi(
      'cn-hongkong',
      'all',
      {
        asset_ids: assetIds,
      },
    );
    if (queuedResult.queued && queuedResult.job_id) {
      message.info('选中代理已加入后台同步队列');
      activeSyncJob.value = queuedResult.job || activeSyncJob.value;
      upsertSyncJobStatus(queuedResult.job || null);
      if (syncJobsOpen.value) {
        await loadSyncJobs(1);
      }
      void monitorCloudAssetSyncJob(queuedResult.job_id)
        .then(async (completedJob) => {
          const result = completedJob?.result || queuedResult;
          activeSyncJob.value = null;
          logCloudSyncConsole('batch-result', result, result?.ok === false);
          await loadData();
          lastSyncTasks.value = result.tasks || [];
          lastSkippedSyncTasks.value = result.skipped_tasks || [];
          if (result?.ok === false || result?.errors?.length) {
            message.warning('选中代理同步完成，但存在错误，请查看同步任务');
            return;
          }
          message.success(`已按选中代理涉及账号同步 ${selectedCount} 条`);
          clearSelectedRows();
        })
        .catch((error: any) => {
          logCloudSyncConsole('batch-error', error, true);
          message.error(error?.message || '批量同步失败');
        });
      return;
    }
    const result = queuedResult;
    logCloudSyncConsole('batch-result', result, result?.ok === false);
    await loadData();
    lastSyncTasks.value = result.tasks || [];
    lastSkippedSyncTasks.value = result.skipped_tasks || [];
    if (result?.ok === false || result?.errors?.length) {
      message.warning('选中代理同步完成，但存在错误，请查看同步摘要');
      return;
    }
    message.success(`已按选中代理涉及账号同步 ${selectedCount} 条`);
    clearSelectedRows();
  } catch (error: any) {
    logCloudSyncConsole('batch-error', error, true);
    message.error(error?.message || '批量同步失败');
  } finally {
    syncing.value = false;
  }
}

async function syncAssets() {
  if (!requireCloudDangerPermission('同步代理')) return;
  if (syncScope.value === 'selected' && selectedAssets.value.length === 0) {
    message.warning('请先选择要同步的代理');
    return;
  }
  syncing.value = true;
  try {
    const providers =
      syncScope.value === 'aws'
        ? ['aws']
        : (syncScope.value === 'aliyun'
          ? ['aliyun']
          : undefined);
    const assetIds =
      syncScope.value === 'selected'
        ? selectedAssets.value.map((asset) => asset.id)
        : undefined;
    logCloudSyncConsole('all-start', {
      scope: syncScope.value,
      providers,
      asset_ids: assetIds,
    });
    const queuedResult = await syncDashboardCloudAssetsApi(
      'cn-hongkong',
      'all',
      {
        providers,
        asset_ids: assetIds,
      },
    );
    if (queuedResult.queued && queuedResult.job_id) {
      message.info('代理同步已加入后台队列');
      activeSyncJob.value = queuedResult.job || activeSyncJob.value;
      upsertSyncJobStatus(queuedResult.job || null);
      if (syncJobsOpen.value) {
        await loadSyncJobs(1);
      }
      void monitorCloudAssetSyncJob(queuedResult.job_id)
        .then(async (completedJob) => {
          const result = completedJob?.result || queuedResult;
          activeSyncJob.value = null;
          logCloudSyncConsole('all-result', result, result?.ok === false);
          markRecentSync();
          await loadData();
          lastSyncTasks.value = result.tasks || [];
          lastSkippedSyncTasks.value = result.skipped_tasks || [];
          if (result?.ok === false || result?.errors?.length) {
            message.warning('代理同步完成，但存在错误，请查看同步任务');
            return;
          }
          message.success(
            `代理同步完成：AWS 存在 ${awsExistingCount.value} 条，阿里云存在 ${aliyunExistingCount.value} 条，未附加IP ${unattachedIpCount.value} 条`,
          );
        })
        .catch((error: any) => {
          logCloudSyncConsole('all-error', error, true);
          message.error(error?.message || '代理同步失败，请查看同步任务');
        });
      return;
    }
    const result = queuedResult;
    logCloudSyncConsole('all-result', result, result?.ok === false);
    markRecentSync();
    await loadData();
    lastSyncTasks.value = result.tasks || [];
    lastSkippedSyncTasks.value = result.skipped_tasks || [];
    if (result?.ok === false || result?.errors?.length) {
      message.warning('代理同步完成，但存在错误，请查看后端同步日志');
      return;
    }
    message.success(
      `代理同步完成：AWS 存在 ${awsExistingCount.value} 条，阿里云存在 ${aliyunExistingCount.value} 条，未附加IP ${unattachedIpCount.value} 条`,
    );
  } catch (error: any) {
    logCloudSyncConsole('all-error', error, true);
    message.error(error?.message || '代理同步失败，请查看后端日志');
  } finally {
    syncing.value = false;
  }
}

function openEdit(record: DashboardCloudAssetItem) {
  if (!requireCloudDangerPermission('编辑代理')) return;
  currentRow.value = record;
  formState.actual_expires_at = record.actual_expires_at
    ? dayjs(record.actual_expires_at)
    : null;
  formState.is_active = record.is_active;
  formState.note = record.note || '';
  formState.price = record.price || '0.00';
  formState.public_ip = record.public_ip || '';
  formState.sort_order = record.sort_order || 99;
  formState.telegram_group_id = record.telegram_group_id || undefined;
  formState.telegram_group_query = record.telegram_group_chat_id
    ? String(record.telegram_group_chat_id)
    : record.telegram_group_username || record.telegram_group_title || '';
  formState.user_query = record.user_id
    ? String(record.user_id)
    : (record.tg_user_id
      ? String(record.tg_user_id)
      : '');
  editOpen.value = true;
}

function toggleLinkExpand(id: number) {
  const key = String(id);
  if (expandedLinkKeys.value.includes(key)) {
    expandedLinkKeys.value = expandedLinkKeys.value.filter(
      (item) => item !== key,
    );
    return;
  }
  expandedLinkKeys.value = [...expandedLinkKeys.value, key];
}

function isLinkExpanded(id: number) {
  return expandedLinkKeys.value.includes(String(id));
}

function toggleNoteExpand(id: number) {
  const key = String(id);
  if (expandedNoteKeys.value.includes(key)) {
    expandedNoteKeys.value = expandedNoteKeys.value.filter(
      (item) => item !== key,
    );
    return;
  }
  expandedNoteKeys.value = [...expandedNoteKeys.value, key];
}

function isNoteExpanded(id: number) {
  return expandedNoteKeys.value.includes(String(id));
}

function toggleUsernameExpand(id: number) {
  const key = String(id);
  if (expandedUsernameKeys.value.includes(key)) {
    expandedUsernameKeys.value = expandedUsernameKeys.value.filter(
      (item) => item !== key,
    );
    return;
  }
  expandedUsernameKeys.value = [...expandedUsernameKeys.value, key];
}

function isUsernameExpanded(id: number) {
  return expandedUsernameKeys.value.includes(String(id));
}

function toggleAssetNameExpand(id: number) {
  const key = String(id);
  if (expandedAssetNameKeys.value.includes(key)) {
    expandedAssetNameKeys.value = expandedAssetNameKeys.value.filter(
      (item) => item !== key,
    );
    return;
  }
  expandedAssetNameKeys.value = [...expandedAssetNameKeys.value, key];
}

function isAssetNameExpanded(id: number) {
  return expandedAssetNameKeys.value.includes(String(id));
}

function countdownTagColor(label?: null | string) {
  if (!label || label === '-') {
    return 'default';
  }
  if (label.includes('未附加IP') || label.includes('未附加固定IP')) {
    return 'warning';
  }
  if (label.includes('仍使用旧机')) {
    return 'warning';
  }
  if (label.includes('迁移中') || label.includes('切换到新机')) {
    return 'processing';
  }
  if (label.includes('已删除')) {
    return 'default';
  }
  if (label.includes('已过期')) {
    return 'error';
  }
  if (label.includes('小时')) {
    return 'warning';
  }
  const matched = label.match(/剩余\s*(\d+)\s*天/);
  if (matched) {
    const days = Number(matched[1]);
    if (days <= 3) {
      return 'gold';
    }
  }
  return 'processing';
}

function sortOrderTagColor(sortOrder?: number) {
  return (sortOrder || 99) === 99 ? 'default' : 'success';
}

function isAutoRenewSaving(id: number) {
  return autoRenewSavingIds.value.includes(id);
}

async function toggleAutoRenew(
  record: DashboardCloudAssetItem,
  enabled: boolean,
) {
  if (!requireCloudDangerPermission('自动续费开关')) return;
  if (!record.user_id) {
    message.error('该代理未绑定用户，无法设置自动续费');
    return;
  }
  if (record.can_auto_renew === false) {
    message.error('该代理当前状态无法设置自动续费');
    return;
  }
  autoRenewSavingIds.value = [...autoRenewSavingIds.value, record.id];
  try {
    const updatedAsset = await toggleDashboardCloudAssetAutoRenewApi(
      record.id,
      enabled,
    );
    replaceAssetInList(updatedAsset);
    message.success(enabled ? '已开启自动续费' : '已关闭自动续费');
  } catch (error: any) {
    message.error(error?.message || '自动续费设置失败');
  } finally {
    autoRenewSavingIds.value = autoRenewSavingIds.value.filter(
      (id) => id !== record.id,
    );
  }
}

async function deleteAsset(record: DashboardCloudAssetItem) {
  if (!requireCloudDangerPermission('删除代理本地状态')) return;
  try {
    await deleteDashboardCloudAssetApi(record.id);
    removeAssetFromList(record.id);
    message.success('代理本地状态已清除；后续同步会按全新资源重新拉回');
  } catch (error: any) {
    message.error(error?.message || '删除代理失败');
  }
}

function startAutoRefresh() {
  if (countdownTimer) {
    clearInterval(countdownTimer);
  }
  resetRefreshCountdown();
  countdownTimer = setInterval(() => {
    if (
      !editOpen.value &&
      !detailOpen.value &&
      !syncJobsOpen.value &&
      !loading.value &&
      !loadingMore.value &&
      !saving.value &&
      !syncing.value
    ) {
      nextRefreshInSeconds.value = Math.max(0, nextRefreshInSeconds.value - 1);
      if (nextRefreshInSeconds.value <= 0) {
        resetRefreshCountdown();
        loadData();
      }
    }
  }, 1000);
}

function stopAutoRefresh() {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  if (syncHighlightTimer) {
    clearTimeout(syncHighlightTimer);
    syncHighlightTimer = null;
  }
}

function normalizedValue(value: null | string | undefined) {
  return value || '';
}

function normalizedDateValue(value: any) {
  if (!value) {
    return '';
  }
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD') : '';
}

function replaceAssetInList(asset: DashboardCloudAssetItem) {
  const index = items.value.findIndex((item) => item.id === asset.id);
  if (index === -1) {
    return;
  }
  items.value = [
    ...items.value.slice(0, index),
    asset,
    ...items.value.slice(index + 1),
  ];
  if (grouped.value) {
    refreshGroupedItems(displayedItems.value);
  }
  currentRow.value = asset;
}

function removeAssetFromList(assetId: number) {
  items.value = items.value.filter((item) => item.id !== assetId);
  loadProgress.loaded = items.value.length;
  loadProgress.total = Math.max(0, loadProgress.total - 1);
  assetPagination.total = Math.max(0, assetPagination.total - 1);
  if (grouped.value) {
    refreshGroupedItems(displayedItems.value);
  }
  if (currentRow.value?.id === assetId) {
    currentRow.value = null;
  }
}

function buildAssetEditPayload(record: DashboardCloudAssetItem) {
  const payload: DashboardCloudAssetUpdatePayload = {};
  const nextExpiresAt = normalizedDateValue(formState.actual_expires_at);
  const previousExpiresAt = normalizedDateValue(record.actual_expires_at);
  if (nextExpiresAt !== previousExpiresAt) {
    payload.actual_expires_at = nextExpiresAt || null;
  }
  const nextIsActive = Boolean(formState.is_active);
  if (nextIsActive !== record.is_active) {
    payload.is_active = nextIsActive;
  }
  const nextNote = formState.note || '';
  if (nextNote !== normalizedValue(record.note)) {
    payload.note = nextNote || null;
  }
  const nextSortOrder = Number(formState.sort_order || 99);
  if (nextSortOrder !== Number(record.sort_order || 99)) {
    payload.sort_order = nextSortOrder;
  }
  const nextPrice = formState.price || '';
  if (nextPrice !== normalizedValue(record.price)) {
    payload.price = nextPrice || null;
  }
  const nextPublicIp = formState.public_ip || '';
  if (nextPublicIp !== normalizedValue(record.public_ip)) {
    payload.public_ip = nextPublicIp || null;
  }
  const previousUserQuery = record.user_id
    ? String(record.user_id)
    : (record.tg_user_id
      ? String(record.tg_user_id)
      : '');
  const nextUserQuery = formState.user_query.trim();
  if (nextUserQuery !== previousUserQuery) {
    payload.user_query = nextUserQuery || null;
  }
  const previousTelegramGroupQuery = record.telegram_group_chat_id
    ? String(record.telegram_group_chat_id)
    : record.telegram_group_username || record.telegram_group_title || '';
  const nextTelegramGroupQuery = formState.telegram_group_query.trim();
  if (nextTelegramGroupQuery === previousTelegramGroupQuery) {
    const nextTelegramGroupId = formState.telegram_group_id || null;
    if (nextTelegramGroupId !== (record.telegram_group_id || null)) {
      payload.telegram_group_id = nextTelegramGroupId;
    }
  } else {
    payload.telegram_group_query = nextTelegramGroupQuery || null;
  }
  return payload;
}

async function submitEdit() {
  if (!requireCloudDangerPermission('保存代理')) return;
  if (!currentRow.value) return;
  saving.value = true;
  try {
    const payload = buildAssetEditPayload(currentRow.value);
    if (Object.keys(payload).length === 0) {
      message.info('没有检测到变更');
      editOpen.value = false;
      return;
    }
    const updatedAsset = await updateDashboardCloudAssetApi(
      currentRow.value.id,
      payload,
    );
    replaceAssetInList(updatedAsset);
    message.success('代理已更新');
    editOpen.value = false;
  } catch (error: any) {
    message.error(error?.message || '更新失败');
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadData();
  loadTelegramGroups();
  startAutoRefresh();
});

onBeforeUnmount(() => {
  stopAutoRefresh();
});
</script>

<template>
  <Page
    description="统一查看 MTProxy 代理资产，支持默认排序与手工排序"
    title="代理列表"
  >
    <Card>
      <template #title>
        <Space class="cloud-assets-toolbar" wrap>
          <span>代理数据</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            class="cloud-assets-search"
            enter-button="搜索"
            placeholder="全量模糊搜索名称、用户、用户名、IP、代理链接、订单号、实例ID、固定IP名、云账号"
            @search="handleSearch"
          />
          <Select
            v-model:value="columnView"
            class="cloud-assets-select"
            :options="columnViewOptions"
            @change="handleColumnViewChange"
          />
          <Select
            v-model:value="syncScope"
            class="cloud-assets-select"
            :options="syncScopeOptions"
          />
          <Button
            size="small"
            :disabled="!canRunCloudDanger"
            :loading="syncing"
            @click="syncAssets"
          >
            同步代理
          </Button>
          <Button
            size="small"
            :disabled="!canRunCloudDanger || selectedAssets.length === 0"
            :loading="syncing"
            @click="batchSyncSelectedAssets"
          >
            批量同步
          </Button>
          <Button
            size="small"
            :disabled="selectedAssets.length === 0"
            @click="copySelectedProxyLinks"
          >
            复制选中链接
          </Button>
          <Button size="small" @click="exportSelectedAssetsCsv">导出CSV</Button>
          <Button
            v-if="selectedAssets.length > 0"
            size="small"
            @click="clearSelectedRows"
          >
            清空选择
          </Button>
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
          <Button size="small" @click="openSyncJobs">同步任务</Button>
          <Tag v-if="selectedAssets.length > 0" color="geekblue">
            已选 {{ selectedAssets.length }} 条
          </Tag>
          <Tag v-if="activeSyncJob" color="processing">
            {{ activeSyncJob.status_label || '同步中' }}
            {{ activeSyncJob.progress_current || 0 }}/{{
              activeSyncJob.progress_total || 0
            }}
          </Tag>
          <Tag v-else-if="syncing" color="processing">同步中…</Tag>
          <Tag v-if="lastSyncTasks.length > 0" color="cyan">
            最近同步 {{ lastSyncTasks.length }} 个账号
          </Tag>
          <Tag v-if="lastSkippedSyncTasks.length > 0" color="warning">
            跳过 {{ lastSkippedSyncTasks.length }} 个账号
          </Tag>
          <Tag v-if="loading" color="processing">刷新中…</Tag>
          <Tag v-if="loadingMore" color="processing">继续加载中…</Tag>
          <Tag color="blue">
            最后刷新：{{ formatRefreshTime(lastRefreshedAt) }}
          </Tag>
          <Tag
            v-if="lastSyncedAt"
            :color="recentSyncHighlight ? 'success' : 'cyan'"
          >
            后台同步：{{ formatRefreshTime(lastSyncedAt) }}
          </Tag>
          <Tag color="geekblue">
            自动同步周期：{{ formatDuration(autoSyncEverySeconds) }}
          </Tag>
          <Tag color="orange">
            数量：AWS {{ awsExistingCount }} / 阿里云
            {{ aliyunExistingCount }}
          </Tag>
          <Tag color="purple">下次刷新：{{ nextRefreshInSeconds }}s</Tag>
          <Space :size="4">
            <span>{{ showDeletedAssets ? '展开已删除' : '折叠已删除' }}</span>
            <Switch
              v-model:checked="showDeletedAssets"
              checked-children="展开"
              un-checked-children="折叠"
              @change="handleDeletedAssetsVisibleChange"
            />
            <Tag color="default">已删除 {{ deletedAssetCount }} 条</Tag>
          </Space>
          <Select
            v-model:value="assetDisplayMode"
            class="cloud-assets-group-select"
            :options="displayModeOptions"
          />
          <Button
            v-if="grouped"
            size="small"
            :disabled="!canExpandAllGroups"
            @click="setAllGroupsExpanded(true)"
          >
            全部展开
          </Button>
          <Button
            v-if="grouped"
            size="small"
            :disabled="!canCollapseAllGroups"
            @click="setAllGroupsExpanded(false)"
          >
            全部折叠
          </Button>
          <Tag v-if="grouped" color="cyan">
            已展开 {{ expandedGroupCount }} / {{ totalGroupCount }} 组
          </Tag>
        </Space>
      </template>

      <div class="asset-field-switches">
        <span class="asset-field-switch-label">显示列：</span>
        <Space class="asset-field-switch-list" wrap>
          <Tag
            v-for="item in assetColumnSwitches"
            :key="item.key"
            :color="assetColumnVisible[item.key] ? 'processing' : 'default'"
            class="asset-field-switch-tag"
          >
            <span>{{ item.label }}</span>
            <Switch
              size="small"
              :checked="assetColumnVisible[item.key]"
              @change="
                (checked) => (assetColumnVisible[item.key] = Boolean(checked))
              "
            />
          </Tag>
        </Space>
      </div>

      <div class="cloud-assets-status-shortcuts">
        <Button
          v-for="option in riskFilterOptions"
          :key="option.value"
          size="small"
          :type="riskStatus === option.value ? 'primary' : 'default'"
          @click="setRiskStatus(option.value)"
        >
          {{ option.label }}
        </Button>
      </div>

      <Collapse
        v-if="grouped"
        v-model:active-key="expandedGroupKeys"
        class="compact-cloud-assets space-y-2"
        @change="handleExpandedGroupKeysChange"
      >
        <Collapse.Panel v-for="group in groups" :key="group.user_key">
          <template #header>
            <Space wrap>
              <span>{{ group.user_display_name }}</span>
              <Tag color="blue">{{ group.username_label || '-' }}</Tag>
              <Tag>
                {{
                  group.telegram_group_id
                    ? group.telegram_group_chat_id || '未绑定群组'
                    : group.tg_user_id || '未绑定用户'
                }}
              </Tag>
              <Tag v-if="group.telegram_group_id" color="green">
                用户：{{ groupUserSummary(group) }}
              </Tag>
              <Tag>{{ activeAssetCount(group.items) }} 条</Tag>
            </Space>
          </template>
          <Table
            v-if="assetTableColumns.length > 0"
            class="cloud-assets-table"
            :columns="assetTableColumns"
            :data-source="group.items"
            :loading="loading"
            :pagination="false"
            :row-selection="assetRowSelection"
            row-key="id"
            :scroll="assetTableScroll"
            size="small"
            @change="handleAssetTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'cloud_user_summary'">
                <Space direction="vertical" :size="2">
                  <span>{{ record.user_display_name || '未绑定用户' }}</span>
                  <TypographyParagraph
                    v-if="
                      usernamePipeLabel(asDashboardCloudAssetItem(record)) !==
                      '-'
                    "
                    :ellipsis="{
                      rows: 1,
                      tooltip: usernamePipeLabel(
                        asDashboardCloudAssetItem(record),
                      ),
                    }"
                    :content="
                      usernamePipeLabel(asDashboardCloudAssetItem(record))
                    "
                    class="mb-0 max-w-full break-all text-xs leading-5"
                  />
                </Space>
              </template>
              <template v-else-if="column.key === 'ip_user_summary'">
                <Space direction="vertical" :size="2">
                  <span>{{ record.user_display_name || '未绑定用户' }}</span>
                  <span class="text-xs text-muted-foreground">
                    {{ usernamePipeLabel(asDashboardCloudAssetItem(record)) }}
                  </span>
                </Space>
              </template>
              <template v-else-if="column.key === 'telegram_group_summary'">
                <Space direction="vertical" :size="2">
                  <span>{{ record.telegram_group_title || '未绑定群组' }}</span>
                  <span class="text-xs text-muted-foreground">
                    {{
                      record.telegram_group_username
                        ? `@${record.telegram_group_username}`
                        : record.telegram_group_chat_id || '-'
                    }}
                  </span>
                </Space>
              </template>
              <template v-else-if="column.key === 'cloud_resource_summary'">
                <Space direction="vertical" :size="2">
                  <TypographyParagraph
                    :ellipsis="{
                      rows: 1,
                      tooltip: record.asset_name || '-',
                    }"
                    :content="record.asset_name || '-'"
                    class="mb-0 max-w-full break-all text-xs leading-5"
                  />
                  <Space :size="4" wrap>
                    <Tag
                      :color="
                        record.provider === 'aws_lightsail' ? 'orange' : 'blue'
                      "
                    >
                      {{ record.provider_label || record.provider || '-' }}
                    </Tag>
                    <Tag v-if="record.region_code" color="geekblue">
                      {{ record.region_code }}
                    </Tag>
                    <span v-else>{{
                      regionDisplay(asDashboardCloudAssetItem(record))
                    }}</span>
                  </Space>
                  <TypographyParagraph
                    v-if="
                      resourceIdLabel(asDashboardCloudAssetItem(record)) !== '-'
                    "
                    :copyable="{
                      text: resourceIdCopyValue(
                        asDashboardCloudAssetItem(record),
                      ),
                    }"
                    :ellipsis="{
                      rows: 1,
                      tooltip: resourceIdLabel(
                        asDashboardCloudAssetItem(record),
                      ),
                    }"
                    :content="
                      resourceIdLabel(asDashboardCloudAssetItem(record))
                    "
                    class="mb-0 max-w-full break-all font-mono text-xs leading-5"
                  />
                </Space>
              </template>
              <template v-else-if="column.key === 'cloud_ip_price'">
                <Space direction="vertical" :size="2">
                  <TypographyParagraph
                    v-if="record.public_ip"
                    :copyable="{ text: record.public_ip }"
                    class="mb-0 font-mono text-xs leading-5"
                  >
                    {{ record.public_ip }}
                  </TypographyParagraph>
                  <span v-else>-</span>
                  <Tag
                    :color="
                      hasAssetPrice(asDashboardCloudAssetItem(record))
                        ? 'success'
                        : 'error'
                    "
                  >
                    {{ assetPriceLabel(asDashboardCloudAssetItem(record)) }}
                  </Tag>
                </Space>
              </template>
              <template v-else-if="column.key === 'username_label'">
                <div
                  v-if="
                    usernamePipeLabel(asDashboardCloudAssetItem(record)) !== '-'
                  "
                  class="max-w-full overflow-hidden"
                >
                  <TypographyParagraph
                    :ellipsis="
                      isUsernameExpanded(record.id)
                        ? false
                        : {
                            rows: 1,
                            tooltip: usernamePipeLabel(
                              asDashboardCloudAssetItem(record),
                            ),
                          }
                    "
                    :content="
                      usernamePipeLabel(asDashboardCloudAssetItem(record))
                    "
                    class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                  />
                  <Button
                    size="small"
                    type="link"
                    class="mt-1 h-auto px-0 py-0"
                    @click="toggleUsernameExpand(record.id)"
                  >
                    {{ isUsernameExpanded(record.id) ? '收起' : '展开' }}
                  </Button>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'asset_name'">
                <div class="max-w-full overflow-hidden">
                  <TypographyParagraph
                    :ellipsis="
                      isAssetNameExpanded(record.id)
                        ? false
                        : { rows: 1, tooltip: record.asset_name || '-' }
                    "
                    :content="record.asset_name || '-'"
                    class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                  />
                  <Button
                    size="small"
                    type="link"
                    class="mt-1 h-auto px-0 py-0"
                    @click="toggleAssetNameExpand(record.id)"
                  >
                    {{ isAssetNameExpanded(record.id) ? '收起' : '展开' }}
                  </Button>
                  <Tag :color="resourceKindColor(record)">
                    {{ resourceKindLabel(record) }}
                  </Tag>
                </div>
              </template>
              <template v-else-if="column.key === 'sort_order'">
                <Tag :color="sortOrderTagColor(record.sort_order)">
                  {{ record.sort_order || 99 }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'provider_label'">
                <Space direction="vertical" :size="2">
                  <Tag
                    :color="
                      record.provider === 'aws_lightsail' ? 'orange' : 'blue'
                    "
                  >
                    {{ record.provider_label || record.provider || '-' }}
                  </Tag>
                </Space>
              </template>
              <template v-else-if="column.key === 'instance_id'">
                <TypographyParagraph
                  v-if="record.instance_id || record.provider_resource_id"
                  :copyable="{
                    text: record.instance_id || record.provider_resource_id,
                  }"
                  :ellipsis="{
                    rows: 2,
                    tooltip: record.instance_id || record.provider_resource_id,
                  }"
                  :content="record.instance_id || record.provider_resource_id"
                  class="mb-0 break-all font-mono text-xs leading-5"
                />
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'account_label'">
                <TypographyParagraph
                  v-if="record.account_label"
                  :copyable="{ text: record.account_label }"
                  class="mb-0 break-all font-mono text-xs leading-5"
                >
                  {{ record.account_label }}
                </TypographyParagraph>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'region_label'">
                <Space direction="vertical" :size="2">
                  <span>{{
                    regionDisplay(asDashboardCloudAssetItem(record))
                  }}</span>
                  <Tag v-if="record.region_code" color="geekblue">
                    {{ record.region_code }}
                  </Tag>
                </Space>
              </template>
              <template v-else-if="column.key === 'price'">
                <Tag
                  :color="
                    hasAssetPrice(asDashboardCloudAssetItem(record))
                      ? 'success'
                      : 'error'
                  "
                >
                  {{ assetPriceLabel(asDashboardCloudAssetItem(record)) }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'auto_renew_enabled'">
                <Space direction="vertical" :size="2">
                  <Tag :color="record.auto_renew_enabled ? 'success' : 'error'">
                    {{ record.auto_renew_enabled ? '已开启' : '已关闭' }}
                  </Tag>
                  <Switch
                    :checked="Boolean(record.auto_renew_enabled)"
                    checked-children="开"
                    un-checked-children="关"
                    :disabled="
                      !canRunCloudDanger ||
                      !record.user_id ||
                      record.can_auto_renew === false
                    "
                    :loading="isAutoRenewSaving(record.id)"
                    @change="
                      (checked) =>
                        toggleAutoRenew(
                          asDashboardCloudAssetItem(record),
                          Boolean(checked),
                        )
                    "
                  />
                </Space>
              </template>
              <template v-else-if="column.key === 'mtproxy_link'">
                <div
                  v-if="
                    buildProxyLinkItems(asDashboardCloudAssetItem(record))
                      .length > 0
                  "
                  class="max-w-full overflow-hidden"
                >
                  <TypographyParagraph
                    :ellipsis="
                      isLinkExpanded(record.id)
                        ? false
                        : {
                            rows: 1,
                            tooltip: buildProxyLinkText(
                              asDashboardCloudAssetItem(record),
                            ),
                          }
                    "
                    :copyable="{
                      text: buildProxyLinkText(
                        asDashboardCloudAssetItem(record),
                      ),
                    }"
                    :content="
                      buildProxyLinkText(asDashboardCloudAssetItem(record))
                    "
                    class="mb-0 max-h-32 overflow-y-auto break-all font-mono text-xs leading-5"
                  />
                  <Space :size="6" class="mt-1">
                    <Button
                      size="small"
                      type="link"
                      class="h-auto px-0 py-0"
                      @click="toggleLinkExpand(record.id)"
                    >
                      {{ isLinkExpanded(record.id) ? '收起' : '展开' }}
                    </Button>
                    <Button
                      size="small"
                      type="link"
                      class="h-auto px-0 py-0"
                      @click="copyProxyLinks(asDashboardCloudAssetItem(record))"
                    >
                      复制全部
                    </Button>
                  </Space>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'network_stats'">
                <Space
                  direction="vertical"
                  :size="2"
                  class="network-stats-cell"
                  :title="
                    networkStatsError(asDashboardCloudAssetItem(record)) ||
                    undefined
                  "
                >
                  <Tag
                    :color="
                      networkSpeedColor(asDashboardCloudAssetItem(record))
                    "
                  >
                    {{ networkSpeedLabel(asDashboardCloudAssetItem(record)) }}
                  </Tag>
                  <div
                    v-if="record.network_stats?.speed_status === 'success'"
                    class="network-speed-values text-xs"
                  >
                    <span>
                      下载速度：{{ record.network_stats.download_mbps || '-' }}
                      Mbps
                    </span>
                    <span>
                      上传速度：{{ record.network_stats.upload_mbps || '-' }}
                      Mbps
                    </span>
                  </div>
                  <span class="text-xs text-muted-foreground">
                    {{ networkTrafficLabel(asDashboardCloudAssetItem(record)) }}
                  </span>
                  <Tag
                    v-if="
                      Number(
                        record.network_stats?.traffic_overflow_bytes || 0,
                      ) > 0
                    "
                    color="error"
                  >
                    超额
                    {{
                      formatNetworkBytes(
                        record.network_stats?.traffic_overflow_bytes,
                      )
                    }}
                  </Tag>
                  <span
                    v-if="networkStatsTime(asDashboardCloudAssetItem(record))"
                    class="text-xs text-muted-foreground"
                  >
                    {{ networkStatsTime(asDashboardCloudAssetItem(record)) }}
                  </span>
                  <Space :size="4">
                    <Button
                      size="small"
                      type="link"
                      class="h-auto px-0 py-0"
                      :disabled="
                        !canRunCloudDanger ||
                        !canRunNetworkCheck(asDashboardCloudAssetItem(record))
                      "
                      :loading="isNetworkSpeedTesting(record.id)"
                      @click="
                        runNetworkSpeedTest(asDashboardCloudAssetItem(record))
                      "
                    >
                      测速
                    </Button>
                    <Button
                      size="small"
                      type="link"
                      class="h-auto px-0 py-0"
                      :disabled="
                        !canRunCloudDanger ||
                        !canRunNetworkCheck(asDashboardCloudAssetItem(record))
                      "
                      :loading="isNetworkTrafficLoading(record.id)"
                      @click="
                        refreshNetworkTraffic(asDashboardCloudAssetItem(record))
                      "
                    >
                      流量
                    </Button>
                  </Space>
                </Space>
              </template>
              <template v-else-if="column.key === 'actual_expires_at'">
                <span>{{
                  record.actual_expires_at
                    ? dayjs(record.actual_expires_at).format('YYYY-MM-DD')
                    : '-'
                }}</span>
              </template>
              <template v-else-if="column.key === 'ip_expiry_summary'">
                <Space direction="vertical" :size="2">
                  <span>
                    {{
                      record.actual_expires_at
                        ? dayjs(record.actual_expires_at).format('YYYY-MM-DD')
                        : '-'
                    }}
                  </span>
                  <Tag
                    :color="
                      countdownTagColor(
                        record.status_countdown ||
                          record.provider_status ||
                          '-',
                      )
                    "
                  >
                    {{
                      record.status_countdown || record.provider_status || '-'
                    }}
                  </Tag>
                </Space>
              </template>
              <template v-else-if="column.key === 'note'">
                <div v-if="record.note" class="max-w-full overflow-hidden">
                  <TypographyParagraph
                    :ellipsis="
                      isNoteExpanded(record.id)
                        ? false
                        : { rows: 1, tooltip: record.note }
                    "
                    :content="record.note"
                    class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                  />
                  <Button
                    size="small"
                    type="link"
                    class="mt-1 h-auto px-0 py-0"
                    @click="toggleNoteExpand(record.id)"
                  >
                    {{ isNoteExpanded(record.id) ? '收起' : '展开' }}
                  </Button>
                </div>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'status'">
                <Tag
                  :color="
                    (record.provider_status || '').includes('未附加固定IP')
                      ? 'warning'
                      : record.status === 'deleted'
                        ? 'default'
                        : record.is_active
                          ? 'success'
                          : record.status === 'terminated'
                            ? 'default'
                            : 'warning'
                  "
                >
                  {{
                    (record.provider_status || '').includes('未附加固定IP')
                      ? '未附加IP'
                      : record.status_label || record.status || '-'
                  }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'provider_status'">
                <Tag
                  :color="
                    ['running', '运行中'].includes(record.provider_status)
                      ? 'success'
                      : 'default'
                  "
                >
                  {{ record.provider_status || '-' }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'status_countdown'">
                <Tag
                  :color="
                    countdownTagColor(
                      record.preserve_link_status ||
                        record.status_countdown ||
                        record.provider_status ||
                        '-',
                    )
                  "
                >
                  {{
                    record.preserve_link_status ||
                    record.status_countdown ||
                    record.provider_status ||
                    '-'
                  }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'actions'">
                <Space class="cloud-assets-actions" :wrap="false">
                  <Button
                    type="link"
                    @click="openDetail(asDashboardCloudAssetItem(record))"
                  >
                    详情
                  </Button>
                  <Button
                    type="link"
                    :disabled="!canRunCloudDanger"
                    @click="openEdit(asDashboardCloudAssetItem(record))"
                  >
                    编辑
                  </Button>
                  <Button
                    type="link"
                    :disabled="!canRunCloudDanger"
                    :loading="isAssetSyncing(record.id)"
                    @click="syncAssetStatus(asDashboardCloudAssetItem(record))"
                  >
                    更新
                  </Button>
                  <Popconfirm
                    title="确认清除这条代理的本地状态吗？不会删除真实云服务器/IP；会清除关联订单的云资源绑定，后续同步按全新资源重新拉回。"
                    @confirm="deleteAsset(asDashboardCloudAssetItem(record))"
                  >
                    <Button danger type="link" :disabled="!canRunCloudDanger">
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              </template>
              <template v-else-if="column.key === 'ip_actions'">
                <Button
                  type="link"
                  :disabled="!canRunCloudDanger"
                  @click="openEdit(asDashboardCloudAssetItem(record))"
                >
                  编辑
                </Button>
              </template>
            </template>
          </Table>
          <Empty v-else description="已关闭全部显示列" />
        </Collapse.Panel>
      </Collapse>

      <div v-if="grouped" class="cloud-assets-pagination mt-4">
        <Pagination
          v-model:current="groupPagination.page"
          v-model:page-size="groupPagination.pageSize"
          :responsive="true"
          show-less-items
          show-quick-jumper
          :show-total="(total: number) => `共 ${total} 个用户/分组`"
          :total="groupPagination.total"
          @change="handleGroupPageChange"
        />
      </div>

      <template v-else>
        <Table
          v-if="assetTableColumns.length > 0"
          class="cloud-assets-table"
          :columns="assetTableColumns"
          :data-source="displayedItems"
          :loading="loading"
          :pagination="{
            current: assetPagination.page,
            pageSize: assetPagination.pageSize,
            responsive: true,
            showQuickJumper: true,
            showSizeChanger: true,
            total: assetPagination.total,
            showTotal: (total: number) => `共 ${total} 条代理`,
          }"
          :row-selection="assetRowSelection"
          row-key="id"
          :scroll="assetTableScroll"
          size="small"
          @change="handleAssetTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'cloud_user_summary'">
              <Space direction="vertical" :size="2">
                <span>{{ record.user_display_name || '未绑定用户' }}</span>
                <TypographyParagraph
                  v-if="
                    usernamePipeLabel(record as DashboardCloudAssetItem) !== '-'
                  "
                  :ellipsis="{
                    rows: 1,
                    tooltip: usernamePipeLabel(
                      record as DashboardCloudAssetItem,
                    ),
                  }"
                  :content="
                    usernamePipeLabel(record as DashboardCloudAssetItem)
                  "
                  class="mb-0 max-w-full break-all text-xs leading-5"
                />
              </Space>
            </template>
            <template v-else-if="column.key === 'ip_user_summary'">
              <Space direction="vertical" :size="2">
                <span>{{ record.user_display_name || '未绑定用户' }}</span>
                <span class="text-xs text-muted-foreground">
                  {{ usernamePipeLabel(asDashboardCloudAssetItem(record)) }}
                </span>
              </Space>
            </template>
            <template v-else-if="column.key === 'telegram_group_summary'">
              <Space direction="vertical" :size="2">
                <span>{{ record.telegram_group_title || '未绑定群组' }}</span>
                <span class="text-xs text-muted-foreground">
                  {{
                    record.telegram_group_username
                      ? `@${record.telegram_group_username}`
                      : record.telegram_group_chat_id || '-'
                  }}
                </span>
              </Space>
            </template>
            <template v-else-if="column.key === 'cloud_resource_summary'">
              <Space direction="vertical" :size="2">
                <TypographyParagraph
                  :ellipsis="{
                    rows: 1,
                    tooltip: record.asset_name || '-',
                  }"
                  :content="record.asset_name || '-'"
                  class="mb-0 max-w-full break-all text-xs leading-5"
                />
                <Space :size="4" wrap>
                  <Tag
                    :color="
                      record.provider === 'aws_lightsail' ? 'orange' : 'blue'
                    "
                  >
                    {{ record.provider_label || record.provider || '-' }}
                  </Tag>
                  <Tag v-if="record.region_code" color="geekblue">
                    {{ record.region_code }}
                  </Tag>
                  <span v-else>{{
                    regionDisplay(record as DashboardCloudAssetItem)
                  }}</span>
                </Space>
                <TypographyParagraph
                  v-if="
                    resourceIdLabel(record as DashboardCloudAssetItem) !== '-'
                  "
                  :copyable="{
                    text: resourceIdCopyValue(
                      record as DashboardCloudAssetItem,
                    ),
                  }"
                  :ellipsis="{
                    rows: 1,
                    tooltip: resourceIdLabel(record as DashboardCloudAssetItem),
                  }"
                  :content="resourceIdLabel(record as DashboardCloudAssetItem)"
                  class="mb-0 max-w-full break-all font-mono text-xs leading-5"
                />
              </Space>
            </template>
            <template v-else-if="column.key === 'cloud_ip_price'">
              <Space direction="vertical" :size="2">
                <TypographyParagraph
                  v-if="record.public_ip"
                  :copyable="{ text: record.public_ip }"
                  class="mb-0 font-mono text-xs leading-5"
                >
                  {{ record.public_ip }}
                </TypographyParagraph>
                <span v-else>-</span>
                <Tag
                  :color="
                    hasAssetPrice(record as DashboardCloudAssetItem)
                      ? 'success'
                      : 'error'
                  "
                >
                  {{ assetPriceLabel(record as DashboardCloudAssetItem) }}
                </Tag>
              </Space>
            </template>
            <template v-else-if="column.key === 'username_label'">
              <div
                v-if="
                  usernamePipeLabel(asDashboardCloudAssetItem(record)) !== '-'
                "
                class="max-w-full overflow-hidden"
              >
                <TypographyParagraph
                  :ellipsis="
                    isUsernameExpanded(record.id)
                      ? false
                      : {
                          rows: 1,
                          tooltip: usernamePipeLabel(
                            asDashboardCloudAssetItem(record),
                          ),
                        }
                  "
                  :content="
                    usernamePipeLabel(asDashboardCloudAssetItem(record))
                  "
                  class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                />
                <Button
                  size="small"
                  type="link"
                  class="mt-1 h-auto px-0 py-0"
                  @click="toggleUsernameExpand(record.id)"
                >
                  {{ isUsernameExpanded(record.id) ? '收起' : '展开' }}
                </Button>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'asset_name'">
              <div class="max-w-full overflow-hidden">
                <TypographyParagraph
                  :ellipsis="
                    isAssetNameExpanded(record.id)
                      ? false
                      : { rows: 1, tooltip: record.asset_name || '-' }
                  "
                  :content="record.asset_name || '-'"
                  class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                />
                <Button
                  size="small"
                  type="link"
                  class="mt-1 h-auto px-0 py-0"
                  @click="toggleAssetNameExpand(record.id)"
                >
                  {{ isAssetNameExpanded(record.id) ? '收起' : '展开' }}
                </Button>
                <Tag :color="resourceKindColor(record)">
                  {{ resourceKindLabel(record) }}
                </Tag>
              </div>
            </template>
            <template v-else-if="column.key === 'sort_order'">
              <Tag :color="sortOrderTagColor(record.sort_order)">
                {{ record.sort_order || 99 }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'provider_label'">
              <Space direction="vertical" :size="2">
                <Tag
                  :color="
                    record.provider === 'aws_lightsail' ? 'orange' : 'blue'
                  "
                >
                  {{ record.provider_label || record.provider || '-' }}
                </Tag>
              </Space>
            </template>
            <template v-else-if="column.key === 'instance_id'">
              <TypographyParagraph
                v-if="record.instance_id || record.provider_resource_id"
                :copyable="{
                  text: record.instance_id || record.provider_resource_id,
                }"
                :ellipsis="{
                  rows: 2,
                  tooltip: record.instance_id || record.provider_resource_id,
                }"
                :content="record.instance_id || record.provider_resource_id"
                class="mb-0 break-all font-mono text-xs leading-5"
              />
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'account_label'">
              <TypographyParagraph
                v-if="record.account_label"
                :copyable="{ text: record.account_label }"
                class="mb-0 break-all font-mono text-xs leading-5"
              >
                {{ record.account_label }}
              </TypographyParagraph>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'region_label'">
              <Space direction="vertical" :size="2">
                <span>{{
                  regionDisplay(asDashboardCloudAssetItem(record))
                }}</span>
                <Tag v-if="record.region_code" color="geekblue">
                  {{ record.region_code }}
                </Tag>
              </Space>
            </template>
            <template v-else-if="column.key === 'price'">
              <Tag
                :color="
                  hasAssetPrice(asDashboardCloudAssetItem(record))
                    ? 'success'
                    : 'error'
                "
              >
                {{ assetPriceLabel(asDashboardCloudAssetItem(record)) }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'auto_renew_enabled'">
              <Space direction="vertical" :size="2">
                <Tag :color="record.auto_renew_enabled ? 'success' : 'error'">
                  {{ record.auto_renew_enabled ? '已开启' : '已关闭' }}
                </Tag>
                <Switch
                  :checked="Boolean(record.auto_renew_enabled)"
                  checked-children="开"
                  un-checked-children="关"
                  :disabled="
                    !canRunCloudDanger ||
                    !record.user_id ||
                    record.can_auto_renew === false
                  "
                  :loading="isAutoRenewSaving(record.id)"
                  @change="
                    (checked) =>
                      toggleAutoRenew(
                        record as DashboardCloudAssetItem,
                        Boolean(checked),
                      )
                  "
                />
              </Space>
            </template>
            <template v-else-if="column.key === 'mtproxy_link'">
              <div
                v-if="
                  buildProxyLinkItems(record as DashboardCloudAssetItem)
                    .length > 0
                "
                class="max-w-full overflow-hidden"
              >
                <TypographyParagraph
                  :ellipsis="
                    isLinkExpanded(record.id)
                      ? false
                      : {
                          rows: 1,
                          tooltip: buildProxyLinkText(
                            record as DashboardCloudAssetItem,
                          ),
                        }
                  "
                  :copyable="{
                    text: buildProxyLinkText(record as DashboardCloudAssetItem),
                  }"
                  :content="
                    buildProxyLinkText(record as DashboardCloudAssetItem)
                  "
                  class="mb-0 max-h-32 overflow-y-auto break-all font-mono text-xs leading-5"
                />
                <Space :size="6" class="mt-1">
                  <Button
                    size="small"
                    type="link"
                    class="h-auto px-0 py-0"
                    @click="toggleLinkExpand(record.id)"
                  >
                    {{ isLinkExpanded(record.id) ? '收起' : '展开' }}
                  </Button>
                  <Button
                    size="small"
                    type="link"
                    class="h-auto px-0 py-0"
                    @click="copyProxyLinks(record as DashboardCloudAssetItem)"
                  >
                    复制全部
                  </Button>
                </Space>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'network_stats'">
              <Space
                direction="vertical"
                :size="2"
                class="network-stats-cell"
                :title="
                  networkStatsError(asDashboardCloudAssetItem(record)) ||
                  undefined
                "
              >
                <Tag
                  :color="networkSpeedColor(asDashboardCloudAssetItem(record))"
                >
                  {{ networkSpeedLabel(asDashboardCloudAssetItem(record)) }}
                </Tag>
                <div
                  v-if="record.network_stats?.speed_status === 'success'"
                  class="network-speed-values text-xs"
                >
                  <span>
                    下载速度：{{ record.network_stats.download_mbps || '-' }}
                    Mbps
                  </span>
                  <span>
                    上传速度：{{ record.network_stats.upload_mbps || '-' }}
                    Mbps
                  </span>
                </div>
                <span class="text-xs text-muted-foreground">
                  {{ networkTrafficLabel(asDashboardCloudAssetItem(record)) }}
                </span>
                <Tag
                  v-if="
                    Number(record.network_stats?.traffic_overflow_bytes || 0) >
                    0
                  "
                  color="error"
                >
                  超额
                  {{
                    formatNetworkBytes(
                      record.network_stats?.traffic_overflow_bytes,
                    )
                  }}
                </Tag>
                <span
                  v-if="networkStatsTime(asDashboardCloudAssetItem(record))"
                  class="text-xs text-muted-foreground"
                >
                  {{ networkStatsTime(asDashboardCloudAssetItem(record)) }}
                </span>
                <Space :size="4">
                  <Button
                    size="small"
                    type="link"
                    class="h-auto px-0 py-0"
                    :disabled="
                      !canRunCloudDanger ||
                      !canRunNetworkCheck(asDashboardCloudAssetItem(record))
                    "
                    :loading="isNetworkSpeedTesting(record.id)"
                    @click="
                      runNetworkSpeedTest(asDashboardCloudAssetItem(record))
                    "
                  >
                    测速
                  </Button>
                  <Button
                    size="small"
                    type="link"
                    class="h-auto px-0 py-0"
                    :disabled="
                      !canRunCloudDanger ||
                      !canRunNetworkCheck(asDashboardCloudAssetItem(record))
                    "
                    :loading="isNetworkTrafficLoading(record.id)"
                    @click="
                      refreshNetworkTraffic(asDashboardCloudAssetItem(record))
                    "
                  >
                    流量
                  </Button>
                </Space>
              </Space>
            </template>
            <template v-else-if="column.key === 'actual_expires_at'">
              <span>{{
                record.actual_expires_at
                  ? dayjs(record.actual_expires_at).format('YYYY-MM-DD')
                  : '-'
              }}</span>
            </template>
            <template v-else-if="column.key === 'ip_expiry_summary'">
              <Space direction="vertical" :size="2">
                <span>
                  {{
                    record.actual_expires_at
                      ? dayjs(record.actual_expires_at).format('YYYY-MM-DD')
                      : '-'
                  }}
                </span>
                <Tag
                  :color="
                    countdownTagColor(
                      record.status_countdown || record.provider_status || '-',
                    )
                  "
                >
                  {{ record.status_countdown || record.provider_status || '-' }}
                </Tag>
              </Space>
            </template>
            <template v-else-if="column.key === 'note'">
              <div v-if="record.note" class="max-w-full overflow-hidden">
                <TypographyParagraph
                  :ellipsis="
                    isNoteExpanded(record.id)
                      ? false
                      : { rows: 1, tooltip: record.note }
                  "
                  :content="record.note"
                  class="mb-0 max-h-24 overflow-y-auto break-all text-xs leading-5"
                />
                <Button
                  size="small"
                  type="link"
                  class="mt-1 h-auto px-0 py-0"
                  @click="toggleNoteExpand(record.id)"
                >
                  {{ isNoteExpanded(record.id) ? '收起' : '展开' }}
                </Button>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag
                :color="
                  (record.provider_status || '').includes('未附加固定IP')
                    ? 'warning'
                    : record.status === 'deleted'
                      ? 'default'
                      : record.is_active
                        ? 'success'
                        : record.status === 'terminated'
                          ? 'default'
                          : 'warning'
                "
              >
                {{
                  (record.provider_status || '').includes('未附加固定IP')
                    ? '未附加IP'
                    : record.status_label || record.status || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'provider_status'">
              <Tag
                :color="
                  ['running', '运行中'].includes(record.provider_status)
                    ? 'success'
                    : 'default'
                "
              >
                {{ record.provider_status || '-' }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'status_countdown'">
              <Tag
                :color="
                  countdownTagColor(
                    record.preserve_link_status ||
                      record.status_countdown ||
                      record.provider_status ||
                      '-',
                  )
                "
              >
                {{
                  record.preserve_link_status ||
                  record.status_countdown ||
                  record.provider_status ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space class="cloud-assets-actions" :wrap="false">
                <Button
                  type="link"
                  @click="openDetail(record as DashboardCloudAssetItem)"
                >
                  详情
                </Button>
                <Button
                  type="link"
                  :disabled="!canRunCloudDanger"
                  @click="openEdit(record as DashboardCloudAssetItem)"
                >
                  编辑
                </Button>
                <Button
                  type="link"
                  :disabled="!canRunCloudDanger"
                  :loading="isAssetSyncing(record.id)"
                  @click="syncAssetStatus(record as DashboardCloudAssetItem)"
                >
                  更新
                </Button>
                <Popconfirm
                  title="确认清除这条代理的本地状态吗？不会删除真实云服务器/IP；会清除关联订单的云资源绑定，后续同步按全新资源重新拉回。"
                  @confirm="deleteAsset(record as DashboardCloudAssetItem)"
                >
                  <Button danger type="link" :disabled="!canRunCloudDanger">
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </template>
            <template v-else-if="column.key === 'ip_actions'">
              <Button
                type="link"
                :disabled="!canRunCloudDanger"
                @click="openEdit(record as DashboardCloudAssetItem)"
              >
                编辑
              </Button>
            </template>
          </template>
        </Table>
        <Empty v-else description="已关闭全部显示列" />
      </template>
    </Card>

    <Drawer
      v-model:open="syncJobsOpen"
      placement="right"
      title="同步任务"
      width="min(860px, 100vw)"
    >
      <div class="sync-job-metrics">
        <div class="sync-job-metric">
          <span>活动</span>
          <strong>{{ syncJobMetrics?.active_count ?? 0 }}</strong>
        </div>
        <div class="sync-job-metric">
          <span>排队/运行</span>
          <strong>
            {{ syncJobMetrics?.queued_count ?? 0 }}/{{
              syncJobMetrics?.running_count ?? 0
            }}
          </strong>
        </div>
        <div class="sync-job-metric">
          <span>近24h失败</span>
          <strong>
            {{ syncJobMetrics?.recent_failed ?? 0 }}/{{
              syncJobMetrics?.recent_total ?? 0
            }}
          </strong>
          <small>{{
            formatSyncFailureRate(syncJobMetrics?.recent_failure_rate)
          }}</small>
        </div>
        <div class="sync-job-metric">
          <span>P95耗时</span>
          <strong>{{
            formatSyncMetricSeconds(syncJobMetrics?.p95_duration_seconds)
          }}</strong>
        </div>
        <div class="sync-job-metric">
          <span>卡住</span>
          <strong>{{ syncJobMetrics?.stale_running_count ?? 0 }}</strong>
        </div>
      </div>
      <Space class="mb-3" wrap>
        <Select
          v-model:value="syncJobsStatusFilter"
          size="small"
          style="width: 132px"
          :options="syncJobStatusFilterOptions"
          @change="handleSyncJobsFilterChange"
        />
        <Switch
          v-model:checked="syncJobsFailedOnly"
          checked-children="仅失败"
          un-checked-children="全部"
          @change="handleSyncJobsFilterChange"
        />
        <Button size="small" :loading="syncJobsLoading" @click="loadSyncJobs()">
          刷新
        </Button>
        <Button
          size="small"
          :loading="syncJobMetricsLoading"
          @click="loadSyncJobMetrics()"
        >
          刷新指标
        </Button>
      </Space>
      <Table
        :columns="syncJobTableColumns"
        :data-source="syncJobs"
        :loading="syncJobsLoading"
        :pagination="{
          current: syncJobsPagination.page,
          pageSize: syncJobsPagination.pageSize,
          showSizeChanger: true,
          total: syncJobsPagination.total,
          showTotal: (total: number) => `共 ${total} 个任务`,
        }"
        row-key="id"
        size="small"
        :scroll="{ x: 980 }"
        @change="handleSyncJobsTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'id'">
            <Space direction="vertical" :size="2">
              <span class="font-mono">#{{ record.id }}</span>
              <TypographyParagraph
                class="!mb-0 max-w-full break-all font-mono text-xs leading-5"
                :copyable="{ text: record.run_id }"
                :ellipsis="{ rows: 1, tooltip: record.run_id }"
              >
                {{ record.run_id }}
              </TypographyParagraph>
            </Space>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="syncJobStatusColor(record.status)">
              {{ record.status_label || record.status }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'scope'">
            <TypographyParagraph
              class="!mb-0 max-w-full break-all text-xs leading-5"
              :ellipsis="{ rows: 2, tooltip: syncJobScopeLabel(record) }"
            >
              {{ syncJobScopeLabel(record) }}
            </TypographyParagraph>
          </template>
          <template v-else-if="column.key === 'progress'">
            <Space direction="vertical" :size="2">
              <span>
                {{ record.progress_current || 0 }}/{{
                  record.progress_total || 0
                }}
              </span>
              <Tag color="blue">{{ record.progress_percent || 0 }}%</Tag>
            </Space>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <Space direction="vertical" :size="2">
              <span>{{ formatTime(record.created_at) }}</span>
              <span class="text-xs text-gray-500">
                {{ formatTime(record.finished_at || record.updated_at) }}
              </span>
              <span class="text-xs text-gray-500">
                {{ syncJobWorkerLabel(record) }}
              </span>
            </Space>
          </template>
          <template v-else-if="column.key === 'errors'">
            <TypographyParagraph
              class="!mb-0 max-w-full break-all text-xs leading-5"
              :ellipsis="{ rows: 2, tooltip: syncJobResultLabel(record) }"
            >
              {{ syncJobResultLabel(record) }}
            </TypographyParagraph>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space :size="4">
              <Button size="small" @click="openSyncJobDetail(record.id)">
                详情
              </Button>
              <Popconfirm
                title="确认取消这个同步任务？运行中的任务会在当前子任务结束后停止。"
                @confirm="cancelSyncJob(record)"
              >
                <Button
                  danger
                  size="small"
                  :disabled="!record.can_cancel || !canRunCloudDanger"
                  :loading="isSyncJobCancelling(record.id)"
                >
                  取消
                </Button>
              </Popconfirm>
              <Button
                size="small"
                :disabled="!record.is_terminal || !canRunCloudDanger"
                :loading="isSyncJobRetrying(record.id)"
                @click="retrySyncJob(record)"
              >
                重试
              </Button>
            </Space>
          </template>
        </template>
        <template #expandedRowRender="{ record }">
          <div class="sync-job-expanded">
            <div class="mb-2">
              <Tag
                v-for="task in record.tasks || []"
                :key="`${record.id}-${task.provider}-${task.region}-${task.command}`"
                color="cyan"
              >
                {{ task.provider || '-' }} / {{ task.region || 'all' }}
              </Tag>
              <Tag
                v-for="task in record.skipped_tasks || []"
                :key="`${record.id}-skip-${task.provider}-${task.region}-${task.reason}`"
                color="warning"
              >
                跳过 {{ task.provider || '-' }} / {{ task.region || 'all' }}
              </Tag>
            </div>
            <TypographyParagraph
              v-if="
                (record.errors || []).length > 0 ||
                (record.warnings || []).length > 0
              "
              class="!mb-2 whitespace-pre-wrap break-all text-xs leading-5"
            >
              {{
                [...(record.errors || []), ...(record.warnings || [])].join(
                  '\n',
                )
              }}
            </TypographyParagraph>
            <TypographyParagraph
              v-if="(record.logs || []).length > 0"
              class="!mb-2 whitespace-pre-wrap break-all font-mono text-xs leading-5"
              :ellipsis="{ rows: 8, expandable: true, symbol: '展开日志' }"
            >
              {{ (record.logs || []).join('\n') }}
            </TypographyParagraph>
            <div
              v-if="(record.events || []).length > 0"
              class="sync-job-events"
            >
              <div
                v-for="event in record.events || []"
                :key="`${record.id}-event-${event.id}`"
                class="sync-job-event-row"
              >
                <Tag :color="syncJobEventColor(event.event_type)">
                  {{ event.event_type_label || event.event_type }}
                </Tag>
                <span class="sync-job-event-time">
                  {{ formatTime(event.created_at) }}
                </span>
                <span class="sync-job-event-message">
                  {{ syncJobEventSummary(event) }}
                </span>
                <span v-if="event.worker_id" class="sync-job-event-worker">
                  {{ event.worker_id }}
                </span>
                <TypographyParagraph
                  v-if="compactJson(event.payload)"
                  class="!mb-0 ml-1 max-w-full whitespace-pre-wrap break-all font-mono text-xs leading-5"
                  :ellipsis="{ rows: 3, expandable: true, symbol: '展开载荷' }"
                >
                  {{ compactJson(event.payload) }}
                </TypographyParagraph>
              </div>
            </div>
          </div>
        </template>
      </Table>
    </Drawer>

    <Drawer
      v-model:open="detailOpen"
      placement="right"
      title="代理详情"
      width="min(720px, 100vw)"
    >
      <div v-if="detailLoading">
        <Tag color="processing">详情加载中…</Tag>
      </div>
      <Empty v-else-if="!detailRow" description="暂无详情" />
      <template v-else>
        <Space class="mb-3" wrap>
          <Button size="small" @click="copyProxyLinks(detailRow)">
            复制全部链接
          </Button>
          <Button size="small" @click="openDetailPage(detailRow.id)">
            打开详情页
          </Button>
          <Button
            size="small"
            :disabled="!canRunCloudDanger || !canRunNetworkCheck(detailRow)"
            :loading="isNetworkSpeedTesting(detailRow.id)"
            @click="runNetworkSpeedTest(detailRow)"
          >
            测速
          </Button>
          <Button
            size="small"
            :disabled="!canRunCloudDanger || !canRunNetworkCheck(detailRow)"
            :loading="isNetworkTrafficLoading(detailRow.id)"
            @click="refreshNetworkTraffic(detailRow)"
          >
            刷新流量
          </Button>
        </Space>
        <Descriptions bordered size="small" :column="2" title="基础信息">
          <Descriptions.Item label="资产名称">
            {{ empty(detailRow.asset_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="来源">
            {{ empty(detailRow.source_label || detailRow.source) }}
          </Descriptions.Item>
          <Descriptions.Item label="厂商">
            {{ empty(detailRow.provider_label || detailRow.provider) }}
          </Descriptions.Item>
          <Descriptions.Item label="地区">
            {{ regionDisplay(detailRow) }}
          </Descriptions.Item>
          <Descriptions.Item label="群组">
            {{ empty(detailRow.telegram_group_title) }}
          </Descriptions.Item>
          <Descriptions.Item label="云账号">
            <TypographyParagraph
              :copyable="
                detailRow.account_label
                  ? { text: detailRow.account_label }
                  : false
              "
              class="!mb-0 break-all font-mono"
            >
              {{ empty(detailRow.account_label) }}
            </TypographyParagraph>
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          class="mt-3"
          size="small"
          :column="2"
          title="测速与本月流量"
        >
          <Descriptions.Item label="连接延迟">
            {{
              detailRow.network_stats?.speed_status === 'success'
                ? `${detailRow.network_stats.latency_ms || '-'} ms`
                : networkSpeedLabel(detailRow)
            }}
          </Descriptions.Item>
          <Descriptions.Item label="下载速度">
            {{
              detailRow.network_stats?.speed_status === 'success'
                ? `${detailRow.network_stats.download_mbps || '-'} Mbps`
                : '-'
            }}
          </Descriptions.Item>
          <Descriptions.Item label="上传速度">
            {{
              detailRow.network_stats?.speed_status === 'success'
                ? `${detailRow.network_stats.upload_mbps || '-'} Mbps`
                : '-'
            }}
          </Descriptions.Item>
          <Descriptions.Item label="本月流量">
            {{ networkTrafficLabel(detailRow) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {{
              formatTime(
                detailRow.network_stats?.traffic_collected_at ||
                  detailRow.network_stats?.speed_tested_at,
              )
            }}
          </Descriptions.Item>
          <Descriptions.Item
            v-if="networkStatsError(detailRow)"
            label="最近错误"
            :span="2"
          >
            {{ networkStatsError(detailRow) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          class="mt-3"
          size="small"
          :column="2"
          title="服务器与 IP"
        >
          <Descriptions.Item label="公网 IP">
            {{ empty(detailRow.public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item label="上一个 IP">
            {{ empty(detailRow.previous_public_ip) }}
          </Descriptions.Item>
          <Descriptions.Item :label="resourceIdKindLabel(detailRow)">
            <TypographyParagraph
              :copyable="
                resourceIdCopyValue(detailRow)
                  ? { text: resourceIdCopyValue(detailRow) }
                  : false
              "
              class="!mb-0 break-all font-mono"
            >
              {{ empty(resourceIdCopyValue(detailRow)) }}
            </TypographyParagraph>
          </Descriptions.Item>
          <Descriptions.Item label="固定 IP 名称">
            {{ empty(detailRow.static_ip_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag :color="statusColor(detailRow.status)">
              {{ empty(detailRow.status_label || detailRow.status) }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="云上状态">
            {{ empty(detailRow.provider_status) }}
          </Descriptions.Item>
          <Descriptions.Item label="剩余">
            {{
              detailRow.preserve_link_status ||
              detailRow.status_countdown ||
              '-'
            }}
          </Descriptions.Item>
          <Descriptions.Item label="到期">
            {{ formatExpiryTime(detailRow.actual_expires_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="最近同步">
            {{ formatTime(detailRow.provider_checked_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {{ formatTime(detailRow.created_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {{ formatTime(detailRow.updated_at) }}
          </Descriptions.Item>
        </Descriptions>

        <Descriptions
          bordered
          class="mt-3"
          size="small"
          :column="2"
          title="用户与订单"
        >
          <Descriptions.Item label="用户">
            {{ empty(detailRow.user_display_name) }}
          </Descriptions.Item>
          <Descriptions.Item label="用户名">
            {{ usernamePipeLabel(detailRow) }}
          </Descriptions.Item>
          <Descriptions.Item label="Telegram ID">
            {{ empty(detailRow.tg_user_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="后台用户 ID">
            {{ empty(detailRow.user_id) }}
          </Descriptions.Item>
          <Descriptions.Item label="订单号">
            <Space v-if="detailRow.order_no">
              <span>{{ detailRow.order_no }}</span>
              <Button
                v-if="detailRow.order_link_path"
                size="small"
                type="link"
                @click="openOrder(detailRow.order_link_path)"
              >
                查看订单
              </Button>
            </Space>
            <span v-else>-</span>
          </Descriptions.Item>
          <Descriptions.Item label="订单状态">
            {{ empty(detailRow.order_status_label || detailRow.order_status) }}
          </Descriptions.Item>
          <Descriptions.Item label="价格">
            {{ assetPriceLabel(detailRow) }}
          </Descriptions.Item>
          <Descriptions.Item label="自动续费">
            {{ detailRow.auto_renew_enabled ? '已开启' : '已关闭' }}
          </Descriptions.Item>
        </Descriptions>

        <div class="mt-3 rounded border border-solid border-gray-200 p-3">
          <div class="mb-2 font-medium">关联订单</div>
          <template v-if="detailRow.related_order">
            <Descriptions bordered :column="2" size="small">
              <Descriptions.Item label="订单号">
                <Space>
                  <span>{{ detailRow.related_order.order_no }}</span>
                  <Button
                    v-if="detailRow.related_order.order_link_path"
                    size="small"
                    type="link"
                    @click="openOrder(detailRow.related_order.order_link_path)"
                  >
                    跳转
                  </Button>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space wrap>
                  <Tag
                    :color="
                      historyOrderTagColor(detailRow.related_order.status)
                    "
                  >
                    {{
                      detailRow.related_order.status_label ||
                      detailRow.related_order.status
                    }}
                  </Tag>
                  <Tag
                    v-for="tag in orderSourceItems(detailRow.related_order)"
                    :key="tag.key"
                    :color="historySourceTagColor(tag.key)"
                  >
                    {{ tag.label }}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="公网 IP">
                {{ empty(detailRow.related_order.public_ip) }}
              </Descriptions.Item>
              <Descriptions.Item label="服务到期">
                {{
                  formatExpiryTime(detailRow.related_order.actual_expires_at)
                }}
              </Descriptions.Item>
            </Descriptions>
          </template>
          <Empty v-else description="暂无关联订单" />
        </div>

        <div class="mt-3 rounded border border-solid border-gray-200 p-3">
          <div class="mb-2 font-medium">历史订单</div>
          <template v-if="detailHistoryOrders.length > 0">
            <div
              v-for="item in detailHistoryOrders"
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
                <Tag v-if="item.id === detailRow.order_id" color="processing">
                  当前关联
                </Tag>
                <Button
                  v-if="item.order_link_path"
                  size="small"
                  type="link"
                  @click="openOrder(item.order_link_path)"
                >
                  查看
                </Button>
              </Space>
              <div
                class="grid grid-cols-1 gap-2 text-sm text-gray-500 md:grid-cols-2"
              >
                <div>公网 IP：{{ empty(item.public_ip) }}</div>
                <div>IP 变更：{{ empty(historyOrderIpChange(item)) }}</div>
                <div>到期：{{ formatExpiryTime(item.actual_expires_at) }}</div>
                <div>创建：{{ formatTime(item.created_at) }}</div>
              </div>
            </div>
          </template>
          <Empty v-else description="暂无历史订单" />
        </div>

        <div class="mt-3 rounded border border-solid border-gray-200 p-3">
          <div class="mb-2 font-medium">代理链接</div>
          <TypographyParagraph
            v-if="buildProxyLinkText(detailRow)"
            :copyable="{ text: buildProxyLinkText(detailRow) }"
            class="break-all font-mono text-xs leading-5"
          >
            {{ buildProxyLinkText(detailRow) }}
          </TypographyParagraph>
          <Empty v-else description="暂无代理链接" />
        </div>

        <div class="mt-3 rounded border border-solid border-gray-200 p-3">
          <div class="mb-2 font-medium">人工备注</div>
          <TypographyParagraph
            v-if="detailRow.note"
            :ellipsis="{ rows: 4, expandable: true, symbol: '展开备注' }"
            class="break-all text-xs leading-5"
          >
            {{ detailRow.note }}
          </TypographyParagraph>
          <Empty v-else description="暂无人工备注" />
        </div>

        <div class="detail-log-list mt-4">
          <div class="mb-2 font-medium">IP / 生命周期日志</div>
          <template v-if="detailLifecycleRows.length > 0">
            <div
              v-for="row in detailLifecycleRows"
              :key="row.id"
              class="detail-log-row"
            >
              <Space class="mb-1" wrap>
                <Tag color="blue">{{ empty(row.event_label) }}</Tag>
                <span>{{ empty(row.executed_at) }}</span>
                <span>{{ empty(row.trigger_label) }}</span>
                <Button
                  v-if="row.order_link_path"
                  class="!px-0"
                  size="small"
                  type="link"
                  @click="openOrder(row.order_link_path)"
                >
                  {{ empty(row.order_no) }}
                </Button>
                <span v-else>{{ empty(row.order_no) }}</span>
              </Space>
              <div class="mb-1 text-xs text-gray-500">
                服务器：{{ empty(row.server_name) }} / 当前 IP：{{
                  empty(row.public_ip)
                }}
                / 上一个 IP：{{ empty(row.previous_public_ip) }}
              </div>
              <TypographyParagraph
                class="!mb-0 whitespace-pre-wrap break-all text-xs leading-5"
                :class="[
                  !lifecycleExpanded(row) &&
                  lifecycleSummaryTooLong(row.summary)
                    ? 'collapsed-note'
                    : '',
                ]"
              >
                {{ empty(row.summary) }}
              </TypographyParagraph>
              <Button
                v-if="lifecycleSummaryTooLong(row.summary)"
                size="small"
                type="link"
                @click="toggleLifecycleSummary(row)"
              >
                {{ lifecycleExpanded(row) ? '收起' : '展开' }}
              </Button>
            </div>
          </template>
          <Empty v-else description="暂无生命周期日志" />
        </div>
      </template>
    </Drawer>

    <Modal
      v-model:open="editOpen"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      title="编辑代理"
      width="min(720px, calc(100vw - 32px))"
      @ok="submitEdit"
    >
      <Form layout="vertical">
        <Form.Item label="用户">
          <Input
            v-model:value="formState.user_query"
            placeholder="输入后台用户ID / Telegram ID / @用户名 / t.me链接；本地没有时用已登录账号解析"
          />
        </Form.Item>
        <Form.Item label="当前显示用户">
          <Input :value="currentRow?.user_display_name || ''" disabled />
        </Form.Item>
        <Form.Item label="绑定群组">
          <Select
            v-model:value="formState.telegram_group_id"
            allow-clear
            show-search
            :filter-option="true"
            :options="telegramGroupOptions()"
            placeholder="选择要绑定的 Telegram 群组"
            @change="handleTelegramGroupSelectChange"
          />
        </Form.Item>
        <Form.Item
          extra="可输入后台群组ID、Telegram 群组 Chat ID、@用户名或群名；留空表示解绑群组。"
          label="群组识别"
        >
          <Input
            v-model:value="formState.telegram_group_query"
            placeholder="例如：1 / -1001234567890 / @groupname / 群名"
          />
        </Form.Item>
        <Form.Item label="当前显示群组">
          <Input :value="currentRow?.telegram_group_title || ''" disabled />
        </Form.Item>
        <Form.Item label="云账号ID">
          <Input :value="currentRow?.account_label || ''" disabled />
        </Form.Item>
        <Form.Item label="价格">
          <Input v-model:value="formState.price" placeholder="关联订单价格" />
        </Form.Item>
        <Form.Item
          extra="这里是服务到期时间；默认值 99 表示不人工干预排序，数字越大越靠前，已删除默认沉底。"
          label="到期日期"
        >
          <DatePicker
            v-model:value="formState.actual_expires_at"
            format="YYYY-MM-DD"
            style="width: 100%"
          />
        </Form.Item>
        <Form.Item label="排序">
          <InputNumber
            v-model:value="formState.sort_order"
            :min="0"
            :precision="0"
            placeholder="99=默认排序"
            style="width: 100%"
          />
        </Form.Item>
        <Form.Item label="公网 IP">
          <Input v-model:value="formState.public_ip" placeholder="x.x.x.x" />
        </Form.Item>
        <Form.Item label="备注">
          <Input v-model:value="formState.note" placeholder="备注信息" />
        </Form.Item>
        <Form.Item label="启用状态">
          <Switch v-model:checked="formState.is_active" />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.cloud-assets-toolbar {
  row-gap: 8px;
  align-items: center;
  width: 100%;
}

.cloud-assets-search {
  flex: 1 1 320px;
  width: min(420px, 100%);
  min-width: 220px;
}

.cloud-assets-select {
  flex: 0 0 120px;
  width: 120px;
}

.cloud-assets-group-select {
  flex: 0 0 130px;
  width: 130px;
}

.cloud-assets-status-shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.cloud-assets-actions {
  flex-wrap: nowrap !important;
  row-gap: 0;
  white-space: nowrap;
}

.network-stats-cell {
  min-width: 0;
  max-width: 100%;
  line-height: 18px;
}

.network-speed-values {
  display: grid;
  gap: 0;
  line-height: 18px;
}

:deep(.ant-card-head-title) {
  min-width: 0;
  padding: 10px 0 !important;
  overflow: visible;
  white-space: normal;
}

:deep(.ant-card-head) {
  min-height: 72px;
  padding-top: 8px;
  padding-bottom: 8px;
}

:deep(.ant-table-wrapper) {
  max-width: 100%;
  overflow: hidden;
}

.cloud-assets-table :deep(.ant-table) {
  table-layout: fixed;
}

.cloud-assets-table :deep(.ant-table-cell) {
  min-width: 0;
  overflow-wrap: anywhere;
}

.cloud-assets-table :deep(.ant-typography) {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.asset-field-switches {
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
  margin-bottom: 12px;
}

.asset-field-switch-label {
  flex: 0 0 auto;
  font-size: 13px;
  color: var(--ant-color-text-secondary);
  white-space: nowrap;
}

.asset-field-switch-list {
  min-width: 0;
}

.asset-field-switch-tag {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 4px 8px;
}

.cloud-assets-pagination {
  display: flex;
  justify-content: flex-end;
  max-width: 100%;
  overflow-x: auto;
}

.compact-cloud-assets :deep(.ant-collapse-header) {
  padding: 6px 12px !important;
}

.compact-cloud-assets :deep(.ant-collapse-content-box) {
  padding: 8px 12px !important;
}

.sync-job-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.sync-job-metric {
  min-width: 0;
  padding: 8px 10px;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.sync-job-metric span,
.sync-job-metric small {
  display: block;
  font-size: 12px;
  line-height: 18px;
  color: #6b7280;
}

@media (max-width: 767px) {
  :deep(.ant-card-body) {
    padding: 12px;
  }

  :deep(.ant-card-head) {
    padding-right: 12px;
    padding-left: 12px;
  }

  .cloud-assets-toolbar {
    align-items: stretch;
  }

  .cloud-assets-toolbar :deep(.ant-space-item) {
    max-width: 100%;
  }

  .cloud-assets-search,
  .cloud-assets-select,
  .cloud-assets-group-select {
    flex: 1 1 100%;
    width: 100%;
    min-width: 0;
  }

  .cloud-assets-toolbar :deep(.ant-btn) {
    min-width: 72px;
  }

  .asset-field-switches {
    flex-direction: column;
    align-items: flex-start;
  }

  .asset-field-switch-tag {
    padding: 3px 6px;
  }

  .cloud-assets-status-shortcuts {
    flex-wrap: nowrap;
    padding-bottom: 4px;
    overflow-x: auto;
  }

  .cloud-assets-status-shortcuts .ant-btn {
    flex: 0 0 auto;
  }

  .compact-cloud-assets :deep(.ant-collapse-header) {
    padding: 6px 8px !important;
  }

  .compact-cloud-assets :deep(.ant-collapse-content-box) {
    padding: 8px 0 !important;
  }

  .cloud-assets-table :deep(.ant-table-cell) {
    padding: 8px 6px !important;
  }

  .cloud-assets-actions :deep(.ant-btn) {
    padding-right: 4px;
    padding-left: 4px;
  }

  .cloud-assets-pagination {
    justify-content: flex-start;
  }
}

.sync-job-metric strong {
  display: block;
  font-size: 18px;
  line-height: 24px;
  color: #111827;
}

.detail-log-list {
  border-top: 1px solid #f0f0f0;
}

.detail-log-row {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.sync-job-expanded {
  padding: 8px 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

@media (max-width: 900px) {
  .sync-job-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.collapsed-note {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

:deep(.ant-table-small .ant-table-thead > tr > th),
:deep(.ant-table-small .ant-table-tbody > tr > td) {
  padding: 4px 8px !important;
}

:deep(.ant-table-small .ant-btn.ant-btn-link) {
  height: auto;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

:deep(.ant-typography) {
  margin-bottom: 0 !important;
  line-height: 1.2 !important;
}
</style>
