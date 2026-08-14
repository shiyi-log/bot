<script lang="ts" setup>
import type {
  DashboardCloudActionSwitchItem,
  DashboardLifecyclePlansDetail,
  DashboardShutdownPlanHistoryItem,
  DashboardShutdownPlanItem,
  DashboardShutdownPlanRunResult,
  DashboardShutdownPlanRunResultItem,
  DashboardSiteConfigGroupItem,
  DashboardUnattachedIpDeletePlan,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  message,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
  TypographyParagraph,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getDashboardLifecyclePlansApi,
  getDashboardSiteConfigGroupsApi,
  initDashboardSiteConfigsApi,
  refreshDashboardLifecyclePlansApi,
  updateDashboardCloudAssetApi,
  updateDashboardLifecyclePlanNoteApi,
  updateDashboardSiteConfigApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const refreshingPlanTable = ref(false);
const planLimit = ref(50);
const keyword = ref('');
const detail = ref<DashboardLifecyclePlansDetail | null>(null);
const lastRunResult = ref<DashboardShutdownPlanRunResult | null>(null);
const failurePanelOpen = ref(false);
const expandedKeys = reactive<Record<string, boolean>>({});
type PlanTableKey =
  | 'ip_delete'
  | 'ip_delete_history'
  | 'server_delete'
  | 'server_history'
  | 'shutdown_plan';
const planPageState = reactive<
  Record<PlanTableKey, { current: number; pageSize: number }>
>({
  ip_delete: { current: 1, pageSize: 50 },
  ip_delete_history: { current: 1, pageSize: 50 },
  server_delete: { current: 1, pageSize: 50 },
  server_history: { current: 1, pageSize: 50 },
  shutdown_plan: { current: 1, pageSize: 50 },
});
const tablePagination = {
  showQuickJumper: true,
  showSizeChanger: true,
  showTotal: (total: number, range: [number, number]) =>
    `${range[0]}-${range[1]} / 共 ${total} 条`,
};
const noteModalOpen = ref(false);
const noteSaving = ref(false);
const noteValue = ref('');
const noteTarget = ref<
  DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan | null
>(null);
const notePreviewOpen = ref(false);
const notePreviewTitle = ref('备注详情');
const notePreviewValue = ref('');
const actionSwitchItems = ref<DashboardCloudActionSwitchItem[]>([]);
const actionSwitchSavingMap = reactive<Record<string, boolean>>({});
const assetShutdownSavingMap = reactive<Record<string, boolean>>({});
const visibleColumnState = reactive<Record<string, boolean>>({});
type LifecyclePlanSwitchField =
  | 'ip_delete_enabled'
  | 'server_delete_enabled'
  | 'shutdown_enabled';

const CLOUD_ACTION_SWITCHES = [
  {
    key: 'cloud_server_shutdown_enabled',
    label: '关机服务器',
  },
  {
    key: 'cloud_server_delete_enabled',
    label: '删除服务器',
  },
  {
    key: 'cloud_ip_delete_enabled',
    label: '删除IP',
  },
];

const fieldSwitchItems = [
  { key: 'ip', label: '服务器IP' },
  { key: 'public_ip', label: 'IP' },
  { key: 'asset_name', label: '固定IP/资产' },
  { key: 'user_display_name', label: '用户' },
  { key: 'note', label: '备注' },
  { key: 'order_no', label: '订单号' },
  { key: 'actual_expires_at', label: '服务到期' },
  { key: 'suspend_at', label: '关机时间' },
  { key: 'delete_at', label: '删除/释放时间' },
  { key: 'resource_state_label', label: '真实状态' },
  { key: 'plan_state_label', label: '计划状态' },
  { key: 'shutdown_enabled', label: '关机开关' },
  { key: 'server_delete_enabled', label: '删机开关' },
  { key: 'ip_delete_enabled', label: 'IP删除开关' },
  { key: 'execution_status', label: '执行状态' },
  { key: 'provider_label', label: '云厂商' },
  { key: 'provider_status', label: '云上状态' },
  { key: 'deletion_source_label', label: '删除来源' },
  { key: 'queue_status', label: '队列状态' },
  { key: 'logged_at', label: '记录时间' },
  { key: 'executed_at', label: '执行时间' },
  { key: 'result_label', label: '结果' },
  { key: 'error', label: '执行错误' },
  { key: 'failure_reason', label: '失败原因' },
  { key: 'actions', label: '操作' },
] as const;

fieldSwitchItems.forEach((item) => {
  visibleColumnState[item.key] = ![
    'deletion_source_label',
    'execution_status',
    'failure_reason',
    'note',
    'order_no',
    'provider_label',
    'provider_status',
    'resource_state_label',
  ].includes(item.key);
});

function dynamicPlanColumns(columns: any[]) {
  return columns.map(({ width: _width, ...column }) => column);
}

const dueColumnsAll = dynamicPlanColumns([
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  { title: '备注', dataIndex: 'note', key: 'note', width: 220 },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 190 },
  {
    title: '服务到期',
    dataIndex: 'actual_expires_at',
    key: 'actual_expires_at',
    width: 180,
  },
  { title: '关机时间', dataIndex: 'suspend_at', key: 'suspend_at', width: 180 },
  { title: '删机时间', dataIndex: 'delete_at', key: 'delete_at', width: 180 },
  {
    title: '真实状态',
    dataIndex: 'resource_state_label',
    key: 'resource_state_label',
    width: 240,
  },
  {
    title: '计划状态',
    dataIndex: 'plan_state_label',
    key: 'plan_state_label',
    width: 160,
  },
  {
    title: '关机计划',
    dataIndex: 'shutdown_enabled',
    key: 'shutdown_enabled',
    width: 120,
  },
  {
    title: '执行状态',
    dataIndex: 'execution_status',
    key: 'execution_status',
    width: 260,
  },
  {
    title: '云厂商',
    dataIndex: 'provider_label',
    key: 'provider_label',
    width: 140,
  },
  { title: '操作', key: 'actions', width: 180, fixed: 'right' as const },
]);

const serverDeleteColumnsAll = dueColumnsAll.map((column) =>
  column.key === 'shutdown_enabled'
    ? {
        ...column,
        dataIndex: 'server_delete_enabled',
        key: 'server_delete_enabled',
        title: '删除计划',
      }
    : column,
);

const serverHistoryColumnsAll = dynamicPlanColumns([
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  { title: '备注', dataIndex: 'note', key: 'note', width: 220 },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 190 },
  { title: '结果', dataIndex: 'result_label', key: 'result_label', width: 120 },
  {
    title: '执行状态',
    dataIndex: 'execution_status',
    key: 'execution_status',
    width: 260,
  },
  {
    title: '删除来源',
    dataIndex: 'deletion_source_label',
    key: 'deletion_source_label',
    width: 140,
  },
  {
    title: '执行时间',
    dataIndex: 'executed_at',
    key: 'executed_at',
    width: 180,
  },
  {
    title: '云厂商',
    dataIndex: 'provider_label',
    key: 'provider_label',
    width: 140,
  },
  { title: '操作', key: 'actions', width: 150, fixed: 'right' as const },
]);

const failureColumns = dynamicPlanColumns([
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 190 },
  {
    title: '队列状态',
    dataIndex: 'queue_status',
    key: 'queue_status',
    width: 140,
  },
  { title: '失败原因', dataIndex: 'error', key: 'error', width: 420 },
]);

const ipDeleteColumnsAll = dynamicPlanColumns([
  { title: 'IP', dataIndex: 'public_ip', key: 'public_ip', width: 150 },
  {
    title: '固定IP/资产',
    dataIndex: 'asset_name',
    key: 'asset_name',
    width: 220,
  },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  { title: '备注', dataIndex: 'note', key: 'note', width: 220 },
  {
    title: '状态',
    dataIndex: 'provider_status',
    key: 'provider_status',
    width: 150,
  },
  {
    title: '真实状态',
    dataIndex: 'resource_state_label',
    key: 'resource_state_label',
    width: 240,
  },
  {
    title: '计划状态',
    dataIndex: 'plan_state_label',
    key: 'plan_state_label',
    width: 160,
  },
  {
    title: 'IP删除计划',
    dataIndex: 'ip_delete_enabled',
    key: 'ip_delete_enabled',
    width: 120,
  },
  {
    title: '删除来源',
    dataIndex: 'deletion_source_label',
    key: 'deletion_source_label',
    width: 140,
  },
  { title: '计划释放', dataIndex: 'delete_at', key: 'delete_at', width: 180 },
  { title: '记录时间', dataIndex: 'logged_at', key: 'logged_at', width: 180 },
  {
    title: '执行状态',
    dataIndex: 'execution_status',
    key: 'execution_status',
    width: 360,
  },
  { title: '操作', key: 'actions', width: 150, fixed: 'right' as const },
]);
const ipDeleteHistoryColumnsAll = ipDeleteColumnsAll.filter(
  (column) => column.key !== 'ip_delete_enabled',
);

function filterPlanColumns(columns: any[]) {
  return columns.filter(
    (column) => visibleColumnState[String(column.key || '')] !== false,
  );
}

const dueColumns = computed(() => filterPlanColumns(dueColumnsAll));
const serverDeleteColumns = computed(() =>
  filterPlanColumns(serverDeleteColumnsAll),
);
const serverHistoryColumns = computed(() =>
  filterPlanColumns(serverHistoryColumnsAll),
);
const ipDeleteColumns = computed(() => filterPlanColumns(ipDeleteColumnsAll));
const ipDeleteHistoryColumns = computed(() =>
  filterPlanColumns(ipDeleteHistoryColumnsAll),
);
const lastRunFailureColumns = computed(() => filterPlanColumns(failureColumns));
const visibleFieldState = computed(() => ({
  execution: [
    'deletion_source_label',
    'error',
    'execution_status',
    'failure_reason',
    'queue_status',
  ].some((key) => visibleColumnState[key] !== false),
  notes: visibleColumnState.note !== false,
  provider:
    visibleColumnState.provider_label !== false ||
    visibleColumnState.provider_status !== false,
}));
const actionSwitchEnabledMap = computed(
  () =>
    Object.fromEntries(
      actionSwitchItems.value.map((item) => [item.key, item.enabled]),
    ) as Record<string, boolean>,
);
const lifecycleFields = computed(() =>
  [
    'basic',
    visibleFieldState.value.notes ? 'notes' : '',
    visibleFieldState.value.execution ? 'execution' : '',
    visibleFieldState.value.provider ? 'provider' : '',
  ]
    .filter(Boolean)
    .join(','),
);
const dueTableScroll = computed(() => ({
  x: 'max-content' as const,
}));
const ipDeleteTableScroll = computed(() => ({
  x: 'max-content' as const,
}));
const summary = computed(() => detail.value);
const shutdownPlanItems = computed(
  () => summary.value?.shutdown_plan_items || [],
);
const serverDeletePlanItems = computed(
  () => summary.value?.server_delete_items || [],
);
const serverHistoryItems = computed(
  () => summary.value?.server_history_items || [],
);
const serverPlanSections = computed(() => [
  {
    columns: dueColumns.value,
    items: shutdownPlanItems.value,
    key: 'shutdown',
    pageKey: 'shutdown_plan' as const,
    switchField: 'shutdown_enabled' as const,
    title: countTitle(
      '关机计划',
      shutdownPlanItems.value.length,
      summary.value?.shutdown_plan_count,
    ),
  },
  {
    columns: serverDeleteColumns.value,
    items: serverDeletePlanItems.value,
    key: 'server-delete',
    pageKey: 'server_delete' as const,
    switchField: 'server_delete_enabled' as const,
    title: countTitle(
      '删除计划',
      serverDeletePlanItems.value.length,
      summary.value?.server_delete_count,
    ),
  },
]);
const ipDeletePlanItems = computed(
  () => summary.value?.ip_delete_plan_items || [],
);
const ipDeleteHistoryItems = computed(
  () => summary.value?.ip_delete_history_items || [],
);
const lastRunFailures = computed(() =>
  (lastRunResult.value?.items || []).filter((item) => !item.ok),
);
const lastRunFailureText = computed(() =>
  lastRunFailures.value
    .map(
      (item) =>
        `${item.ip || item.order_no}: ${item.error || '服务器删除失败'}`,
    )
    .join('\n'),
);

function countTitle(label: string, loaded: number, total?: number) {
  if (typeof total === 'number' && total > loaded) {
    return `${label}（已加载 ${loaded} / 总 ${total}）`;
  }
  return `${label}（${total ?? loaded}）`;
}

function planPagination(
  key: PlanTableKey,
  loaded: number,
  fallbackTotal?: number,
) {
  const state = planPageState[key];
  const meta = summary.value?.pagination?.[key];
  const total = meta?.total ?? fallbackTotal ?? loaded;
  return {
    ...tablePagination,
    current: state.current,
    pageSize: state.pageSize,
    total,
  };
}

async function handlePlanPageChange(key: PlanTableKey, pagination: any) {
  const nextPageSize = Number(
    pagination?.pageSize || planPageState[key].pageSize,
  );
  const pageSizeChanged = nextPageSize !== planPageState[key].pageSize;
  const nextPage = Number(pagination?.current || 1);
  planPageState[key].current = pageSizeChanged ? 1 : Math.max(nextPage, 1);
  planPageState[key].pageSize = Math.max(nextPageSize, 1);
  await loadData({ silent: true, tables: [key] });
}

function resetPlanPages() {
  (Object.keys(planPageState) as PlanTableKey[]).forEach((key) => {
    planPageState[key].current = 1;
  });
}

function fmtTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD') : '-';
}

function fmtRecordTime(record: any, key: unknown) {
  return fmtTime(String(key || '') ? record[String(key)] : null);
}

function recordTimeColor(record: any, key: unknown) {
  const value = String(key || '') ? record[String(key)] : null;
  return dueColor(value, Boolean(value && dayjs(value).isBefore(dayjs())));
}

function rowKey(record: {
  asset_id?: null | number | string;
  asset_name?: null | string;
  id?: null | number | string;
  ip?: null | string;
  order_id?: null | number | string;
  order_no?: null | string;
  plan_item_key?: null | string;
  public_ip?: null | string;
  source_id?: null | number | string;
  source_kind?: null | string;
}) {
  return String(
    record.plan_item_key ||
      (record.source_kind && record.source_id
        ? `${record.source_kind}:${record.source_id}`
        : '') ||
      record.asset_id ||
      record.order_id ||
      record.order_no ||
      record.public_ip ||
      record.ip ||
      record.asset_name ||
      'unknown',
  );
}

function isExpanded(key: string) {
  return Boolean(expandedKeys[key]);
}

function toggleExpanded(key: string) {
  expandedKeys[key] = !expandedKeys[key];
}

function dueColor(value?: null | string, overdue?: boolean) {
  if (overdue) return 'error';
  if (!value) return 'default';
  const target = dayjs(value);
  if (!target.isValid()) return 'default';
  const hours = target.diff(dayjs(), 'hour', true);
  if (hours <= 0) return 'red';
  if (hours <= 12) return 'red';
  if (hours <= 24) return 'volcano';
  if (hours <= 72) return 'orange';
  if (hours <= 168) return 'gold';
  if (hours <= 360) return 'lime';
  if (hours <= 720) return 'green';
  if (hours <= 1440) return 'cyan';
  return 'blue';
}

function resourceStateColor(state?: string) {
  if (
    [
      'cloud_missing',
      'instance_deleted',
      'instance_deleted_ip_retained',
    ].includes(String(state || ''))
  )
    return 'success';
  if (String(state || '') === 'missing_confirming') return 'warning';
  if (String(state || '') === 'fixed_ip_unattached') return 'processing';
  if (String(state || '') === 'instance_present') return 'error';
  return 'default';
}

function planStateColor(state?: string) {
  if (String(state || '') === 'completed') return 'success';
  if (
    [
      'blocked',
      'ip_delete_disabled',
      'server_delete_disabled',
      'shutdown_disabled',
    ].includes(String(state || ''))
  )
    return 'warning';
  if (String(state || '') === 'scheduled') return 'processing';
  if (String(state || '') === 'pending') return 'error';
  return 'default';
}

function globalActionSwitchKey(field: LifecyclePlanSwitchField) {
  if (field === 'shutdown_enabled') return 'cloud_server_shutdown_enabled';
  if (field === 'server_delete_enabled') return 'cloud_server_delete_enabled';
  return 'cloud_ip_delete_enabled';
}

function globalActionSwitchLabel(field: LifecyclePlanSwitchField) {
  if (field === 'shutdown_enabled') return '关机服务器';
  if (field === 'server_delete_enabled') return '删除服务器';
  return '删除IP';
}

function isGlobalActionEnabled(field: LifecyclePlanSwitchField) {
  return actionSwitchEnabledMap.value[globalActionSwitchKey(field)] !== false;
}

function disabledPlanStateKey(field: LifecyclePlanSwitchField) {
  if (field === 'shutdown_enabled') return 'shutdown_disabled';
  if (field === 'server_delete_enabled') return 'server_delete_disabled';
  return 'ip_delete_disabled';
}

function disabledPlanStateLabel(field: LifecyclePlanSwitchField) {
  if (field === 'shutdown_enabled') return '总开关关闭';
  if (field === 'server_delete_enabled') return '删机总开关关闭';
  return 'IP删除总开关关闭';
}

function disabledExecutionStatus(field: LifecyclePlanSwitchField) {
  if (field === 'shutdown_enabled') {
    return '关机服务器总开关关闭，当前只保留计划展示，不允许真实关机';
  }
  if (field === 'server_delete_enabled') {
    return '删除服务器总开关关闭，当前只保留计划展示，不允许真实删机';
  }
  return '删除IP总开关关闭，当前只保留计划展示，不允许真实释放 IP';
}

function effectivePlanState(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
  field: LifecyclePlanSwitchField,
) {
  return isGlobalActionEnabled(field)
    ? record.plan_state
    : disabledPlanStateKey(field);
}

function effectivePlanStateLabel(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
  field: LifecyclePlanSwitchField,
) {
  return isGlobalActionEnabled(field)
    ? record.plan_state_label || '-'
    : disabledPlanStateLabel(field);
}

function effectiveBlockedReason(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
  field: LifecyclePlanSwitchField,
) {
  return isGlobalActionEnabled(field)
    ? record.blocked_reason
    : `${globalActionSwitchLabel(field)}总开关当前为关闭状态，需先开启总开关后再执行单项计划。`;
}

function effectiveExecutionText(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
  field: LifecyclePlanSwitchField,
) {
  return isGlobalActionEnabled(field)
    ? executionText(record)
    : disabledExecutionStatus(field);
}

function assetPlanSwitchDisabled(field: LifecyclePlanSwitchField) {
  return !canRunCloudDanger.value || !isGlobalActionEnabled(field);
}

function serverPlanSwitchField(key: unknown) {
  return String(key) === 'server_delete_enabled'
    ? 'server_delete_enabled'
    : 'shutdown_enabled';
}

function serverPlanSwitchLabel(key: unknown) {
  return String(key) === 'server_delete_enabled' ? '删除计划' : '关机计划';
}

function executionText(record: {
  execution_status?: null | string;
  note?: null | string;
}) {
  return record.execution_status || record.note || '-';
}

function executionPlan(record: { execution_plan?: string }) {
  return record.execution_plan || '-';
}

function planNote(record: {
  display_note?: null | string;
  note?: null | string;
  source_note?: null | string;
}) {
  return record.display_note || record.note || record.source_note || '-';
}

function compactCellText(text?: null | string) {
  return String(text || '-')
    .replaceAll(/\s*\n+\s*/g, ' / ')
    .replaceAll(/\s{2,}/g, ' ')
    .trim();
}

function expandedCellKey(
  prefix: string,
  record: {
    id: null | number;
    order_id?: null | number;
    plan_item_key?: string;
  },
) {
  return `${prefix}-${rowKey(record)}`;
}

function cellEllipsis(
  prefix: string,
  record: {
    id: null | number;
    order_id?: null | number;
    plan_item_key?: string;
  },
  text?: null | string,
  rows = 2,
) {
  return isExpanded(expandedCellKey(prefix, record))
    ? false
    : { rows, tooltip: text || '-' };
}

function shouldShowCellExpand(
  text?: null | string,
  extraText?: null | string,
  threshold = 48,
) {
  return Boolean(`${text || ''}${extraText || ''}`.length > threshold);
}

function openNotePreview(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
) {
  const targetIp = String(
    (record as any).ip || (record as any).public_ip || '',
  ).trim();
  notePreviewTitle.value = `备注详情${targetIp ? ` · ${targetIp}` : ''}`;
  notePreviewValue.value = planNote(record);
  notePreviewOpen.value = true;
}

function openNoteEditor(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
) {
  noteTarget.value = record;
  noteValue.value = record.note || '';
  noteModalOpen.value = true;
}

function actionSwitchLabel(key: string) {
  return CLOUD_ACTION_SWITCHES.find((item) => item.key === key)?.label || key;
}

function toActionSwitchItem(item: DashboardSiteConfigGroupItem) {
  const label = actionSwitchLabel(item.key);
  return {
    description: item.description || '',
    enabled: String(item.value || '').trim() === '1',
    id: item.id,
    key: item.key,
    label,
  };
}

async function loadActionSwitches() {
  const groups = await getDashboardSiteConfigGroupsApi({
    group: 'cloud_actions',
  });
  actionSwitchItems.value = (groups[0]?.items || []).map((groupItem) =>
    toActionSwitchItem(groupItem),
  );
}

async function toggleActionSwitch(
  item: DashboardCloudActionSwitchItem,
  checked: boolean,
) {
  if (!requireCloudDangerPermission(`切换${item.label}总开关`)) return;
  actionSwitchSavingMap[item.key] = true;
  try {
    if (!item.id) {
      await initDashboardSiteConfigsApi({ scope: 'configs' });
      await loadActionSwitches();
      const refreshed = actionSwitchItems.value.find(
        (candidate) => candidate.key === item.key,
      );
      if (!refreshed?.id) {
        throw new Error('配置初始化失败，请刷新后重试');
      }
      item = refreshed;
    }
    const configId = item.id;
    if (!configId) {
      throw new Error('配置不存在，请刷新后重试');
    }
    const saved = await updateDashboardSiteConfigApi(configId, {
      is_sensitive: false,
      key: item.key,
      value: checked ? '1' : '0',
    });
    item.enabled = String(saved.value || '').trim() === '1';
    message.success(`${item.label}已${item.enabled ? '开启' : '关闭'}`);
  } catch (error: any) {
    item.enabled = !checked;
    message.error(error?.message || `${item.label}切换失败`);
  } finally {
    actionSwitchSavingMap[item.key] = false;
  }
}

async function toggleAssetPlanSwitch(
  record: DashboardShutdownPlanItem | DashboardUnattachedIpDeletePlan,
  checked: boolean,
  field: 'ip_delete_enabled' | 'server_delete_enabled' | 'shutdown_enabled',
  switchLabel: string,
) {
  const assetId = Number((record as any).asset_id || 0);
  if (!assetId) {
    message.error(`缺少资产 ID，无法切换${switchLabel}`);
    return;
  }
  const key = `${assetId}:${field}`;
  assetShutdownSavingMap[key] = true;
  try {
    const result = await updateDashboardCloudAssetApi(assetId, {
      [field]: checked,
    });
    (record as any)[field] = Boolean((result as any)[field]);
    message.success(
      `${switchLabel}已${(result as any)[field] ? '开启' : '关闭'}`,
    );
    await loadData({ silent: true });
  } catch (error: any) {
    (record as any)[field] = !checked;
    message.error(error?.message || `${switchLabel}切换失败`);
  } finally {
    assetShutdownSavingMap[key] = false;
  }
}

async function savePlanNote() {
  const target = noteTarget.value;
  if (!target || noteSaving.value) return;
  const payload: {
    asset_id?: number;
    item_type?: string;
    note: string;
    order_id?: number;
  } = {
    item_type: (target as DashboardShutdownPlanItem).item_type || 'asset',
    note: noteValue.value,
  };
  const orderTarget = target as DashboardShutdownPlanItem;
  if (orderTarget.item_type === 'order') {
    payload.order_id = Number(orderTarget.order_id || 0);
  } else {
    payload.asset_id = Number(orderTarget.asset_id || 0);
  }
  noteSaving.value = true;
  try {
    const result = await updateDashboardLifecyclePlanNoteApi(payload);
    target.note = result.note || '';
    target.display_note = result.display_note || '';
    message.success('备注已保存');
    noteModalOpen.value = false;
    await loadData({ silent: true });
  } catch (error: any) {
    message.error(error?.message || '备注保存失败');
  } finally {
    noteSaving.value = false;
  }
}

function openPath(path?: string) {
  if (path) router.push(path).catch(() => {});
}

function goBack() {
  router.push('/admin/cloud-assets').catch(() => {});
}

function mergeLifecyclePlanDetail(
  current: DashboardLifecyclePlansDetail,
  incoming: DashboardLifecyclePlansDetail,
): DashboardLifecyclePlansDetail {
  return {
    ...current,
    ...incoming,
    ip_delete_history_items:
      incoming.ip_delete_history_items ?? current.ip_delete_history_items,
    ip_delete_plan_items:
      incoming.ip_delete_plan_items ?? current.ip_delete_plan_items,
    pagination: {
      ...current.pagination,
      ...incoming.pagination,
    },
    server_delete_items:
      incoming.server_delete_items ?? current.server_delete_items,
    server_history_items:
      incoming.server_history_items ?? current.server_history_items,
    shutdown_plan_items:
      incoming.shutdown_plan_items ?? current.shutdown_plan_items,
  };
}

async function loadData(options?: {
  silent?: boolean;
  tables?: PlanTableKey[];
}) {
  if (!options?.silent) loading.value = true;
  try {
    const requestLimit = Math.max(
      planPageState.ip_delete.pageSize,
      planPageState.ip_delete_history.pageSize,
      planPageState.server_delete.pageSize,
      planPageState.server_history.pageSize,
      planPageState.shutdown_plan.pageSize,
    );
    const result = await getDashboardLifecyclePlansApi({
      compact: 1,
      fields: lifecycleFields.value,
      ip_delete_history_page: planPageState.ip_delete_history.current,
      ip_delete_history_page_size: planPageState.ip_delete_history.pageSize,
      ip_delete_page: planPageState.ip_delete.current,
      ip_delete_page_size: planPageState.ip_delete.pageSize,
      keyword: keyword.value.trim() || undefined,
      limit: requestLimit,
      server_delete_page: planPageState.server_delete.current,
      server_delete_page_size: planPageState.server_delete.pageSize,
      server_history_page: planPageState.server_history.current,
      server_history_page_size: planPageState.server_history.pageSize,
      shutdown_page: planPageState.shutdown_plan.current,
      shutdown_page_size: planPageState.shutdown_plan.pageSize,
      tables: options?.tables?.join(','),
    });
    detail.value =
      options?.tables?.length && detail.value
        ? mergeLifecyclePlanDetail(detail.value, result)
        : result;
  } catch (error: any) {
    message.error(error?.message || '计划加载失败');
    detail.value = null;
  } finally {
    loading.value = false;
  }
}

async function toggleVisibleField(key: string, checked: boolean) {
  visibleColumnState[key] = checked;
  await loadData();
}

async function searchPlans() {
  resetPlanPages();
  await loadData();
}

async function resetSearch() {
  keyword.value = '';
  resetPlanPages();
  await loadData();
}

async function loadMorePlans() {
  planLimit.value += 50;
  (Object.keys(planPageState) as PlanTableKey[]).forEach((key) => {
    planPageState[key].current = 1;
    planPageState[key].pageSize = planLimit.value;
  });
  await loadData();
}

async function refreshPlanTable() {
  refreshingPlanTable.value = true;
  try {
    const result = await refreshDashboardLifecyclePlansApi({
      limit: planLimit.value,
    });
    const activeCount =
      result.source_asset_count ??
      result.shutdown_plan_count + result.server_delete_count;
    message.success(`计划已刷新：${activeCount} 条`);
    await loadData({ silent: true });
  } catch (error: any) {
    message.error(error?.message || '刷新计划失败');
  } finally {
    refreshingPlanTable.value = false;
  }
}

onMounted(() => {
  loadData();
  loadActionSwitches().catch((error: any) => {
    message.error(error?.message || '计划开关加载失败');
  });
});
</script>

<template>
  <Page
    class="plans-page"
    description="按代理列表资产生成关机、删除和 IP 删除计划，并查看执行历史"
    title="计划"
  >
    <Space direction="vertical" style="width: 100%" :size="16">
      <Card :loading="loading">
        <template #title>
          <Space wrap>
            <Input.Search
              v-model:value="keyword"
              allow-clear
              class="plans-search"
              placeholder="搜索 IP / 用户 / 订单号 / 备注"
              size="small"
              @search="searchPlans"
            />
            <Button size="small" @click="resetSearch">重置</Button>
            <Button size="small" @click="goBack">返回代理列表</Button>
            <Button size="small" :loading="loading" @click="loadData()">
              刷新
            </Button>
            <Button
              size="small"
              :loading="refreshingPlanTable"
              @click="refreshPlanTable"
            >
              刷新计划表
            </Button>
            <Button size="small" :loading="loading" @click="loadMorePlans">
              加载更多
            </Button>
            <span>{{ summary?.task_label || '计划' }}</span>
            <Tag color="processing">
              {{ summary?.status_label || '独立计划页' }}
            </Tag>
            <Tag :color="refreshingPlanTable ? 'warning' : 'default'">
              {{
                refreshingPlanTable
                  ? '计划表刷新中'
                  : `最后刷新：${fmtTime(summary?.last_refresh_at)}`
              }}
            </Tag>
            <div class="plan-action-switches">
              <div
                v-for="item in actionSwitchItems"
                :key="item.key"
                class="plan-action-switch"
              >
                <span class="plan-action-switch-label">{{ item.label }}</span>
                <Switch
                  :checked="item.enabled"
                  checked-children="开启"
                  :disabled="!canRunCloudDanger"
                  :loading="actionSwitchSavingMap[item.key]"
                  size="small"
                  un-checked-children="关闭"
                  @change="
                    (checked) => toggleActionSwitch(item, Boolean(checked))
                  "
                />
              </div>
            </div>
          </Space>
        </template>
        <Alert
          type="info"
          show-icon
          :message="`当前按 ${planLimit} 条分批加载；数据很多时可继续加载更多。`"
          style="margin-bottom: 12px"
        />
        <div class="plan-field-switches">
          <span class="plan-field-switch-label">显示列：</span>
          <Space wrap>
            <Tag
              v-for="item in fieldSwitchItems"
              :key="item.key"
              :color="visibleColumnState[item.key] ? 'processing' : 'default'"
              class="plan-field-switch-tag"
            >
              <span>{{ item.label }}</span>
              <Switch
                size="small"
                :checked="visibleColumnState[item.key]"
                @change="
                  (checked) => toggleVisibleField(item.key, Boolean(checked))
                "
              />
            </Tag>
          </Space>
        </div>
        <Descriptions bordered :column="2" size="small">
          <Descriptions.Item label="下次执行">
            {{ fmtTime(summary?.next_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="上次执行">
            {{ fmtTime(summary?.last_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="计划表最后刷新">
            {{ fmtTime(summary?.last_refresh_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="刷新状态">
            <Tag :color="refreshingPlanTable ? 'warning' : 'success'">
              {{ refreshingPlanTable ? '刷新中' : '空闲' }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="当前计划资产">
            {{ summary?.source_asset_count ?? 0 }} 条
          </Descriptions.Item>
          <Descriptions.Item label="缺少到期时间">
            <Tag
              :color="
                (summary?.missing_expiry_count || 0) > 0 ? 'warning' : 'success'
              "
            >
              {{ summary?.missing_expiry_count ?? 0 }} 条
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="未附加IP">
            <Tag
              :color="
                (summary?.unattached_ip_count || 0) > 0 ? 'warning' : 'success'
              "
            >
              {{ summary?.unattached_ip_count ?? 0 }} 条
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="服务器资产">
            {{ summary?.server_asset_count ?? 0 }} 条
          </Descriptions.Item>
          <Descriptions.Item label="服务器删除历史">
            {{ summary?.server_history_count ?? 0 }} 条
          </Descriptions.Item>
          <Descriptions.Item label="最近24小时失败">
            <Tag
              :color="
                (summary?.recent_failure_count || 0) > 0 ? 'error' : 'success'
              "
            >
              {{ summary?.recent_failure_count ?? 0 }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="IP删除历史">
            {{ summary?.ip_delete_history_count ?? 0 }} 条
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card v-if="lastRunFailures.length > 0" title="本次执行失败面板">
        <Alert
          type="error"
          show-icon
          :message="`本次执行失败 ${lastRunFailures.length} 条`"
          description="以下为刚刚手动执行产生的失败原因，方便直接定位处理。"
          style="margin-bottom: 12px"
        />
        <Table
          :columns="lastRunFailureColumns"
          :data-source="lastRunFailures"
          :pagination="tablePagination"
          :row-key="rowKey"
          :scroll="dueTableScroll"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'error'">
              <TypographyParagraph class="mb-0 break-all text-sm leading-6">
                {{
                  (record as DashboardShutdownPlanRunResultItem).error || '-'
                }}
              </TypographyParagraph>
            </template>
          </template>
        </Table>
      </Card>

      <Card
        v-for="section in serverPlanSections"
        :key="section.key"
        :title="section.title"
      >
        <Table
          class="plans-compact-table"
          size="small"
          :columns="section.columns"
          :data-source="section.items"
          :loading="loading"
          :pagination="
            planPagination(
              section.pageKey,
              section.items.length,
              section.pageKey === 'shutdown_plan'
                ? summary?.shutdown_plan_count
                : summary?.server_delete_count,
            )
          "
          :row-key="rowKey"
          :scroll="dueTableScroll"
          @change="
            (pagination) => handlePlanPageChange(section.pageKey, pagination)
          "
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user_display_name'">
              <div>
                <div>{{ (record as any).user_display_name || '-' }}</div>
                <div
                  v-if="(record as any).username_label"
                  style="color: var(--color-text-secondary)"
                  class="text-xs"
                >
                  {{ (record as any).username_label }}
                </div>
              </div>
            </template>
            <template
              v-else-if="
                ['actual_expires_at', 'suspend_at', 'delete_at'].includes(
                  String(column.key),
                )
              "
            >
              <Tag :color="recordTimeColor(record, column.key)">
                {{ fmtRecordTime(record, column.key) }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'resource_state_label'">
              <Tag
                :color="
                  resourceStateColor(
                    (record as DashboardShutdownPlanItem).resource_state,
                  )
                "
              >
                {{
                  (record as DashboardShutdownPlanItem).resource_state_label ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'plan_state_label'">
              <div>
                <Tag
                  :color="
                    planStateColor(
                      effectivePlanState(
                        record as DashboardShutdownPlanItem,
                        section.switchField,
                      ),
                    )
                  "
                >
                  {{
                    effectivePlanStateLabel(
                      record as DashboardShutdownPlanItem,
                      section.switchField,
                    )
                  }}
                </Tag>
                <TypographyParagraph
                  v-if="
                    effectiveBlockedReason(
                      record as DashboardShutdownPlanItem,
                      section.switchField,
                    )
                  "
                  :content="
                    effectiveBlockedReason(
                      record as DashboardShutdownPlanItem,
                      section.switchField,
                    ) || '-'
                  "
                  class="mb-0 mt-1 break-all text-xs leading-5"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="
                    cellEllipsis(
                      'shutdown-plan-state',
                      record as DashboardShutdownPlanItem,
                      effectiveBlockedReason(
                        record as DashboardShutdownPlanItem,
                        section.switchField,
                      ),
                      2,
                    )
                  "
                />
                <Button
                  v-if="
                    shouldShowCellExpand(
                      effectiveBlockedReason(
                        record as DashboardShutdownPlanItem,
                        section.switchField,
                      ),
                    )
                  "
                  type="link"
                  size="small"
                  class="mt-1 h-auto px-0 py-0"
                  @click="
                    toggleExpanded(
                      expandedCellKey(
                        'shutdown-plan-state',
                        record as DashboardShutdownPlanItem,
                      ),
                    )
                  "
                >
                  {{
                    isExpanded(
                      expandedCellKey(
                        'shutdown-plan-state',
                        record as DashboardShutdownPlanItem,
                      ),
                    )
                      ? '收起'
                      : '展开'
                  }}
                </Button>
              </div>
            </template>
            <template
              v-else-if="
                ['shutdown_enabled', 'server_delete_enabled'].includes(
                  String(column.key),
                )
              "
            >
              <Switch
                :checked="(record as any)[String(column.key)] !== false"
                :disabled="
                  assetPlanSwitchDisabled(serverPlanSwitchField(column.key))
                "
                :loading="
                  assetShutdownSavingMap[
                    `${(record as DashboardShutdownPlanItem).asset_id || ''}:${String(column.key)}`
                  ]
                "
                checked-children="开"
                un-checked-children="关"
                @change="
                  (checked) =>
                    toggleAssetPlanSwitch(
                      record as DashboardShutdownPlanItem,
                      Boolean(checked),
                      serverPlanSwitchField(column.key),
                      serverPlanSwitchLabel(column.key),
                    )
                "
              />
            </template>
            <template v-else-if="column.key === 'execution_status'">
              <div>
                <TypographyParagraph
                  :content="
                    effectiveExecutionText(
                      record as DashboardShutdownPlanItem,
                      section.switchField,
                    )
                  "
                  class="mb-0 break-all text-xs leading-5"
                  :ellipsis="
                    cellEllipsis(
                      'shutdown-exec',
                      record as DashboardShutdownPlanItem,
                      effectiveExecutionText(
                        record as DashboardShutdownPlanItem,
                        section.switchField,
                      ),
                    )
                  "
                />
                <TypographyParagraph
                  :content="`执行计划：${(record as DashboardShutdownPlanItem).execution_plan || '-'}`"
                  class="mb-0 text-xs"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="
                    cellEllipsis(
                      'shutdown-exec-plan',
                      record as DashboardShutdownPlanItem,
                      `执行计划：${(record as DashboardShutdownPlanItem).execution_plan || '-'}`,
                      1,
                    )
                  "
                />
                <Button
                  v-if="
                    shouldShowCellExpand(
                      (record as DashboardShutdownPlanItem).execution_status,
                      (record as DashboardShutdownPlanItem).execution_plan,
                    )
                  "
                  type="link"
                  size="small"
                  class="mt-1 h-auto px-0 py-0"
                  @click="
                    toggleExpanded(
                      expandedCellKey(
                        'shutdown-exec',
                        record as DashboardShutdownPlanItem,
                      ),
                    );
                    toggleExpanded(
                      expandedCellKey(
                        'shutdown-exec-plan',
                        record as DashboardShutdownPlanItem,
                      ),
                    );
                  "
                >
                  {{
                    isExpanded(
                      expandedCellKey(
                        'shutdown-exec',
                        record as DashboardShutdownPlanItem,
                      ),
                    )
                      ? '收起'
                      : '展开'
                  }}
                </Button>
              </div>
            </template>
            <template v-else-if="column.key === 'note'">
              <div>
                <TypographyParagraph
                  :content="planNote(record as any)"
                  class="note-cell-text mb-0 whitespace-pre-wrap break-all text-xs leading-5"
                  :ellipsis="
                    cellEllipsis(
                      'shutdown-note',
                      record as any,
                      planNote(record as any),
                      2,
                    )
                  "
                />
                <Button
                  v-if="
                    shouldShowCellExpand(planNote(record as any), undefined, 36)
                  "
                  type="link"
                  size="small"
                  class="note-expand-btn"
                  @click="openNotePreview(record as any)"
                >
                  查看
                </Button>
              </div>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space :size="4">
                <Button
                  v-if="visibleColumnState.note"
                  type="link"
                  size="small"
                  @click="openNoteEditor(record as DashboardShutdownPlanItem)"
                >
                  备注
                </Button>
                <Button
                  type="link"
                  size="small"
                  @click="
                    openPath((record as DashboardShutdownPlanItem).related_path)
                  "
                >
                  资产详情
                </Button>
              </Space>
            </template>
          </template>
        </Table>
      </Card>

      <Card
        :title="
          countTitle(
            'IP删除计划',
            ipDeletePlanItems.length,
            summary?.ip_delete_count,
          )
        "
      >
        <Table
          class="plans-compact-table"
          size="small"
          :columns="ipDeleteColumns"
          :data-source="ipDeletePlanItems"
          :loading="loading"
          :pagination="
            planPagination(
              'ip_delete',
              ipDeletePlanItems.length,
              summary?.ip_delete_count,
            )
          "
          :row-key="rowKey"
          :scroll="ipDeleteTableScroll"
          @change="
            (pagination) => handlePlanPageChange('ip_delete', pagination)
          "
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'provider_status'">
              <Tag
                :color="
                  (record as DashboardUnattachedIpDeletePlan).is_overdue
                    ? 'error'
                    : 'warning'
                "
              >
                {{
                  (record as DashboardUnattachedIpDeletePlan).provider_status ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'user_display_name'">
              <div>
                <div>{{ (record as any).user_display_name || '-' }}</div>
                <div
                  v-if="(record as any).username_label"
                  style="color: var(--color-text-secondary)"
                  class="text-xs"
                >
                  {{ (record as any).username_label }}
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'resource_state_label'">
              <Tag
                :color="
                  resourceStateColor(
                    (record as DashboardUnattachedIpDeletePlan).resource_state,
                  )
                "
              >
                {{
                  (record as DashboardUnattachedIpDeletePlan)
                    .resource_state_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'plan_state_label'">
              <div>
                <Tag
                  :color="
                    planStateColor(
                      effectivePlanState(
                        record as DashboardUnattachedIpDeletePlan,
                        'ip_delete_enabled',
                      ),
                    )
                  "
                >
                  {{
                    effectivePlanStateLabel(
                      record as DashboardUnattachedIpDeletePlan,
                      'ip_delete_enabled',
                    )
                  }}
                </Tag>
                <TypographyParagraph
                  v-if="
                    effectiveBlockedReason(
                      record as DashboardUnattachedIpDeletePlan,
                      'ip_delete_enabled',
                    )
                  "
                  :content="
                    compactCellText(
                      effectiveBlockedReason(
                        record as DashboardUnattachedIpDeletePlan,
                        'ip_delete_enabled',
                      ),
                    )
                  "
                  class="mb-0 break-all text-xs leading-5"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="{
                    rows: 1,
                    tooltip: effectiveBlockedReason(
                      record as DashboardUnattachedIpDeletePlan,
                      'ip_delete_enabled',
                    ),
                  }"
                />
              </div>
            </template>
            <template v-else-if="column.key === 'deletion_source_label'">
              <Tag color="blue">
                {{
                  (record as DashboardUnattachedIpDeletePlan)
                    .deletion_source_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'ip_delete_enabled'">
              <Switch
                :checked="
                  (record as DashboardUnattachedIpDeletePlan)
                    .ip_delete_enabled !== false
                "
                :disabled="assetPlanSwitchDisabled('ip_delete_enabled')"
                :loading="
                  assetShutdownSavingMap[
                    `${String(
                      (record as DashboardUnattachedIpDeletePlan).asset_id ||
                        '',
                    )}:ip_delete_enabled`
                  ]
                "
                checked-children="开"
                un-checked-children="关"
                @change="
                  (checked) =>
                    toggleAssetPlanSwitch(
                      record as DashboardUnattachedIpDeletePlan,
                      Boolean(checked),
                      'ip_delete_enabled',
                      'IP删除计划',
                    )
                "
              />
            </template>
            <template v-else-if="column.key === 'delete_at'">
              <Tag
                :color="
                  dueColor(
                    (record as DashboardUnattachedIpDeletePlan).delete_at,
                    (record as DashboardUnattachedIpDeletePlan).is_overdue,
                  )
                "
              >
                {{
                  fmtTime((record as DashboardUnattachedIpDeletePlan).delete_at)
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'logged_at'">
              {{
                fmtTime((record as DashboardUnattachedIpDeletePlan).logged_at)
              }}
            </template>
            <template v-else-if="column.key === 'execution_status'">
              <div>
                <TypographyParagraph
                  :content="
                    effectiveExecutionText(
                      record as DashboardUnattachedIpDeletePlan,
                      'ip_delete_enabled',
                    )
                  "
                  :ellipsis="
                    cellEllipsis(
                      'ip-plan-exec',
                      record as DashboardUnattachedIpDeletePlan,
                      effectiveExecutionText(
                        record as DashboardUnattachedIpDeletePlan,
                        'ip_delete_enabled',
                      ),
                    )
                  "
                  class="mb-0 break-all text-xs leading-5"
                />
                <TypographyParagraph
                  v-if="
                    executionPlan(record as DashboardUnattachedIpDeletePlan) !==
                    '-'
                  "
                  :content="`执行计划：${executionPlan(record as DashboardUnattachedIpDeletePlan)}`"
                  class="mb-0 text-xs"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="
                    cellEllipsis(
                      'ip-plan-exec-plan',
                      record as DashboardUnattachedIpDeletePlan,
                      `执行计划：${executionPlan(record as DashboardUnattachedIpDeletePlan)}`,
                      1,
                    )
                  "
                />
              </div>
            </template>
            <template v-else-if="column.key === 'note'">
              <TypographyParagraph
                :content="planNote(record as any)"
                class="note-cell-text mb-0 whitespace-pre-wrap break-all text-xs leading-5"
                :ellipsis="
                  cellEllipsis(
                    'ip-plan-note',
                    record as any,
                    planNote(record as any),
                    2,
                  )
                "
              />
              <Button
                v-if="
                  shouldShowCellExpand(planNote(record as any), undefined, 36)
                "
                type="link"
                size="small"
                class="note-expand-btn"
                @click="openNotePreview(record as any)"
              >
                查看
              </Button>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space :size="4">
                <Button
                  type="link"
                  size="small"
                  @click="
                    openNoteEditor(record as DashboardUnattachedIpDeletePlan)
                  "
                >
                  备注
                </Button>
                <Button
                  type="link"
                  size="small"
                  @click="
                    openPath(
                      (record as DashboardUnattachedIpDeletePlan).detail_path ||
                        (record as DashboardUnattachedIpDeletePlan)
                          .asset_detail_path,
                    )
                  "
                >
                  详情
                </Button>
              </Space>
            </template>
          </template>
        </Table>
        <Empty
          v-if="ipDeletePlanItems.length === 0 && !loading"
          description="当前没有 IP 删除计划"
        />
      </Card>

      <Card
        :title="
          countTitle(
            'IP 删除历史记录',
            ipDeleteHistoryItems.length,
            summary?.ip_delete_history_count,
          )
        "
      >
        <Table
          class="plans-compact-table"
          size="small"
          :columns="ipDeleteHistoryColumns"
          :data-source="ipDeleteHistoryItems"
          :loading="loading"
          :pagination="
            planPagination(
              'ip_delete_history',
              ipDeleteHistoryItems.length,
              summary?.ip_delete_history_count,
            )
          "
          :row-key="rowKey"
          :scroll="ipDeleteTableScroll"
          @change="
            (pagination) =>
              handlePlanPageChange('ip_delete_history', pagination)
          "
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'provider_status'">
              <Tag
                :color="
                  (record as DashboardUnattachedIpDeletePlan).is_overdue
                    ? 'error'
                    : 'warning'
                "
              >
                {{
                  (record as DashboardUnattachedIpDeletePlan).provider_status ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'user_display_name'">
              <div>
                <div>{{ (record as any).user_display_name || '-' }}</div>
                <div
                  v-if="(record as any).username_label"
                  style="color: var(--color-text-secondary)"
                  class="text-xs"
                >
                  {{ (record as any).username_label }}
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'resource_state_label'">
              <Tag
                :color="
                  resourceStateColor(
                    (record as DashboardUnattachedIpDeletePlan).resource_state,
                  )
                "
              >
                {{
                  (record as DashboardUnattachedIpDeletePlan)
                    .resource_state_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'plan_state_label'">
              <div>
                <Tag
                  :color="
                    planStateColor(
                      (record as DashboardUnattachedIpDeletePlan).plan_state,
                    )
                  "
                >
                  {{
                    (record as DashboardUnattachedIpDeletePlan)
                      .plan_state_label || '-'
                  }}
                </Tag>
                <TypographyParagraph
                  v-if="
                    (record as DashboardUnattachedIpDeletePlan).blocked_reason
                  "
                  :content="
                    compactCellText(
                      (record as DashboardUnattachedIpDeletePlan)
                        .blocked_reason,
                    )
                  "
                  class="mb-0 break-all text-xs leading-5"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="{
                    rows: 1,
                    tooltip: (record as DashboardUnattachedIpDeletePlan)
                      .blocked_reason,
                  }"
                />
              </div>
            </template>
            <template v-else-if="column.key === 'deletion_source_label'">
              <Tag color="blue">
                {{
                  (record as DashboardUnattachedIpDeletePlan)
                    .deletion_source_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'delete_at'">
              <Tag
                :color="
                  dueColor(
                    (record as DashboardUnattachedIpDeletePlan).delete_at,
                    (record as DashboardUnattachedIpDeletePlan).is_overdue,
                  )
                "
              >
                {{
                  fmtTime((record as DashboardUnattachedIpDeletePlan).delete_at)
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'logged_at'">
              {{
                fmtTime((record as DashboardUnattachedIpDeletePlan).logged_at)
              }}
            </template>
            <template v-else-if="column.key === 'execution_status'">
              <div>
                <TypographyParagraph
                  :content="
                    executionText(record as DashboardUnattachedIpDeletePlan)
                  "
                  :ellipsis="
                    cellEllipsis(
                      'ip-history-exec',
                      record as DashboardUnattachedIpDeletePlan,
                      executionText(record as DashboardUnattachedIpDeletePlan),
                    )
                  "
                  class="mb-0 break-all text-xs leading-5"
                />
                <TypographyParagraph
                  v-if="
                    executionPlan(record as DashboardUnattachedIpDeletePlan) !==
                    '-'
                  "
                  :content="`执行计划：${executionPlan(record as DashboardUnattachedIpDeletePlan)}`"
                  class="mb-0 text-xs"
                  style="color: var(--color-text-secondary)"
                  :ellipsis="
                    cellEllipsis(
                      'ip-history-exec-plan',
                      record as DashboardUnattachedIpDeletePlan,
                      `执行计划：${executionPlan(record as DashboardUnattachedIpDeletePlan)}`,
                      1,
                    )
                  "
                />
                <Button
                  v-if="
                    shouldShowCellExpand(
                      executionText(record as DashboardUnattachedIpDeletePlan),
                      executionPlan(
                        record as DashboardUnattachedIpDeletePlan,
                      ) === '-'
                        ? ''
                        : executionPlan(
                            record as DashboardUnattachedIpDeletePlan,
                          ),
                    )
                  "
                  type="link"
                  size="small"
                  class="h-auto px-0 py-0"
                  @click="
                    toggleExpanded(
                      expandedCellKey(
                        'ip-history-exec',
                        record as DashboardUnattachedIpDeletePlan,
                      ),
                    );
                    toggleExpanded(
                      expandedCellKey(
                        'ip-history-exec-plan',
                        record as DashboardUnattachedIpDeletePlan,
                      ),
                    );
                  "
                >
                  {{
                    isExpanded(
                      expandedCellKey(
                        'ip-history-exec',
                        record as DashboardUnattachedIpDeletePlan,
                      ),
                    )
                      ? '收起'
                      : '展开'
                  }}
                </Button>
              </div>
            </template>
            <template v-else-if="column.key === 'note'">
              <TypographyParagraph
                :content="planNote(record as any)"
                class="note-cell-text mb-0 whitespace-pre-wrap break-all text-xs leading-5"
                :ellipsis="
                  cellEllipsis(
                    'ip-history-note',
                    record as any,
                    planNote(record as any),
                    2,
                  )
                "
              />
              <Button
                v-if="
                  shouldShowCellExpand(planNote(record as any), undefined, 36)
                "
                type="link"
                size="small"
                class="note-expand-btn"
                @click="openNotePreview(record as any)"
              >
                查看
              </Button>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                type="link"
                size="small"
                @click="
                  openPath(
                    (record as DashboardUnattachedIpDeletePlan).detail_path ||
                      (record as DashboardUnattachedIpDeletePlan)
                        .asset_detail_path,
                  )
                "
              >
                查看详情
              </Button>
            </template>
          </template>
        </Table>
        <Empty
          v-if="ipDeleteHistoryItems.length === 0 && !loading"
          description="当前没有 IP 删除历史记录"
        />
      </Card>

      <Card
        :title="
          countTitle(
            '服务器删除历史记录',
            serverHistoryItems.length,
            summary?.server_history_count,
          )
        "
      >
        <Table
          class="plans-compact-table"
          size="small"
          :columns="serverHistoryColumns"
          :data-source="serverHistoryItems"
          :loading="loading"
          :pagination="
            planPagination(
              'server_history',
              serverHistoryItems.length,
              summary?.server_history_count,
            )
          "
          :row-key="rowKey"
          :scroll="dueTableScroll"
          @change="
            (pagination) => handlePlanPageChange('server_history', pagination)
          "
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user_display_name'">
              <div>
                <div>{{ (record as any).user_display_name || '-' }}</div>
                <div
                  v-if="(record as any).username_label"
                  style="color: var(--color-text-secondary)"
                  class="text-xs"
                >
                  {{ (record as any).username_label }}
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'result_label'">
              <Tag
                :color="
                  (record as DashboardShutdownPlanHistoryItem).is_success
                    ? 'success'
                    : 'error'
                "
              >
                {{
                  (record as DashboardShutdownPlanHistoryItem).result_label ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'deletion_source_label'">
              <Tag color="blue">
                {{
                  (record as DashboardShutdownPlanHistoryItem)
                    .deletion_source_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'executed_at'">
              {{
                fmtTime(
                  (record as DashboardShutdownPlanHistoryItem).executed_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'execution_status'">
              <TypographyParagraph
                :content="
                  executionText(record as DashboardShutdownPlanHistoryItem)
                "
                class="mb-0 break-all text-xs leading-5"
                :ellipsis="
                  cellEllipsis(
                    'server-history-exec',
                    record as any,
                    executionText(record as DashboardShutdownPlanHistoryItem),
                  )
                "
              />
            </template>
            <template v-else-if="column.key === 'note'">
              <TypographyParagraph
                :content="planNote(record as DashboardShutdownPlanHistoryItem)"
                class="note-cell-text mb-0 whitespace-pre-wrap break-all text-xs leading-5"
                :ellipsis="
                  cellEllipsis(
                    'server-history-note',
                    record as any,
                    planNote(record as DashboardShutdownPlanHistoryItem),
                    2,
                  )
                "
              />
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                type="link"
                size="small"
                @click="
                  openPath(
                    (record as DashboardShutdownPlanHistoryItem).detail_path ||
                      (record as DashboardShutdownPlanHistoryItem).related_path,
                  )
                "
              >
                查看详情
              </Button>
            </template>
          </template>
        </Table>
        <Empty
          v-if="serverHistoryItems.length === 0 && !loading"
          description="当前没有服务器删除历史记录"
        />
      </Card>
    </Space>
    <Modal
      v-model:open="failurePanelOpen"
      title="服务器删除失败原因"
      width="760px"
      :footer="null"
    >
      <Alert
        type="error"
        show-icon
        :message="`失败 ${lastRunFailures.length} 条`"
        description="服务器删除执行已完成，以下 IP 失败，需要按原因处理后重试。"
        style="margin-bottom: 12px"
      />
      <TypographyParagraph
        :copyable="lastRunFailureText ? { text: lastRunFailureText } : false"
        class="mb-3 whitespace-pre-wrap break-all text-sm leading-6"
      >
        {{ lastRunFailureText || '暂无失败原因' }}
      </TypographyParagraph>
      <Table
        :columns="lastRunFailureColumns"
        :data-source="lastRunFailures"
        :pagination="tablePagination"
        :row-key="rowKey"
        :scroll="dueTableScroll"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'error'">
            <TypographyParagraph class="mb-0 break-all text-sm leading-6">
              {{ (record as DashboardShutdownPlanRunResultItem).error || '-' }}
            </TypographyParagraph>
          </template>
        </template>
      </Table>
    </Modal>
    <Modal
      v-model:open="noteModalOpen"
      title="编辑备注"
      :confirm-loading="noteSaving"
      @ok="savePlanNote"
    >
      <Input.TextArea
        v-model:value="noteValue"
        :auto-size="{ minRows: 4, maxRows: 10 }"
        placeholder="填写删除计划备注"
      />
    </Modal>
    <Modal
      v-model:open="notePreviewOpen"
      :title="notePreviewTitle"
      width="720px"
      :footer="null"
    >
      <TypographyParagraph
        class="mb-0 whitespace-pre-wrap break-all text-sm leading-6"
      >
        {{ notePreviewValue || '-' }}
      </TypographyParagraph>
    </Modal>
  </Page>
</template>
<style scoped>
.plan-action-switches {
  display: inline-flex;
  gap: 14px;
  align-items: center;
  min-height: 24px;
  padding-left: 12px;
  border-left: 1px solid var(--ant-color-border-secondary);
}

.plan-action-switch {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  white-space: nowrap;
}

.plan-action-switch-label {
  font-size: 12px;
  color: var(--ant-color-text-secondary);
}

.plan-field-switches {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.plans-search {
  width: 280px;
}

.plan-field-switch-label {
  font-size: 13px;
  color: var(--ant-color-text-secondary);
  white-space: nowrap;
}

.plan-field-switch-tag {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 4px 8px;
}

.plans-page :deep(.plans-compact-table .ant-table-thead > tr > th) {
  padding-top: 10px;
  padding-bottom: 10px;
}

.plans-page :deep(.plans-compact-table .ant-table-tbody > tr > td) {
  padding-top: 8px;
  padding-bottom: 8px;
  vertical-align: middle;
}

.plans-page :deep(.plans-compact-table .ant-table-cell > div) {
  min-height: 20px;
}

.plans-page
  :deep(
    .plans-compact-table
      .ant-table-cell
      > div
      > div.text-xs:not(.note-cell-text)
  ) {
  display: none;
}

.plans-page :deep(.plans-compact-table .ant-typography) {
  max-width: 100%;
  margin-bottom: 0 !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap !important;
}

.plans-page :deep(.plans-compact-table .mt-1.h-auto.px-0.py-0),
.plans-page :deep(.plans-compact-table .h-auto.px-0.py-0) {
  display: none;
}

.plans-page :deep(.plans-compact-table .note-cell-text) {
  display: block;
  max-width: 100%;
  max-height: 40px;
  overflow: hidden;
  line-height: 20px;
  overflow-wrap: anywhere;
  white-space: normal !important;
}

.plans-page
  :deep(.plans-compact-table .note-cell-text.ant-typography-ellipsis) {
  max-height: 40px;
}

.plans-page
  :deep(.plans-compact-table .note-cell-text:not(.ant-typography-ellipsis)) {
  max-height: 40px;
}

.plans-page :deep(.plans-compact-table .note-expand-btn) {
  display: inline-flex !important;
  margin-top: 2px;
}

.plans-page :deep(.plans-compact-table .ant-btn-link.ant-btn-sm) {
  min-height: 20px;
}
</style>
