<script lang="ts" setup>
import type {
  DashboardAutoRenewRunResult,
  DashboardAutoRenewRunResultItem,
  DashboardAutoRenewTaskDetail,
  DashboardAutoRenewTaskDueItem,
  DashboardAutoRenewTaskHistoryItem,
} from '#/api/admin';

import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  message,
  Modal,
  Segmented,
  Space,
  Table,
  Tag,
  TypographyParagraph,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getDashboardAutoRenewRunApi,
  getDashboardAutoRenewTaskDetailApi,
  runDashboardAutoRenewOrderApi,
  runDashboardAutoRenewTasksApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const runningAll = ref(false);
const runningOrderIds = reactive<Record<number, boolean>>({});
const detail = ref<DashboardAutoRenewTaskDetail | null>(null);
const lastRunResult = ref<DashboardAutoRenewRunResult | null>(null);
const failurePanelOpen = ref(false);
const historyPage = ref(1);
const historyLimit = ref(10);
const historyResult = ref<'all' | 'failure' | 'success'>('all');
const historyResultOptions = [
  { label: '全部', value: 'all' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failure' },
];
let runPollTimer: null | ReturnType<typeof setTimeout> = null;
let watchedRunId = '';
let runPollFailures = 0;

const dueColumns = [
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  {
    title: '队列状态',
    dataIndex: 'queue_status_label',
    key: 'queue_status_label',
    width: 150,
  },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 190 },
  {
    title: '到期时间',
    dataIndex: 'actual_expires_at',
    key: 'actual_expires_at',
    width: 180,
  },
  {
    title: '自动续费时间',
    dataIndex: 'auto_renew_at',
    key: 'auto_renew_at',
    width: 180,
  },
  {
    title: '下次巡检',
    dataIndex: 'next_run_at',
    key: 'next_run_at',
    width: 180,
  },
  { title: '余额', dataIndex: 'balance', key: 'balance', width: 140 },
  { title: '计划', dataIndex: 'plan', key: 'plan', width: 220 },
  { title: '操作', key: 'actions', width: 180, fixed: 'right' as const },
];

const failureColumns = [
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 190 },
  {
    title: '队列状态',
    dataIndex: 'queue_status',
    key: 'queue_status',
    width: 140,
  },
  { title: '失败原因', dataIndex: 'error', key: 'error', width: 420 },
];

const historyColumns = [
  {
    title: '执行时间',
    dataIndex: 'executed_at',
    key: 'executed_at',
    width: 180,
  },
  { title: 'IP', dataIndex: 'ip', key: 'ip', width: 150 },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 180,
  },
  { title: '结果', dataIndex: 'result_label', key: 'result_label', width: 100 },
  {
    title: '余额变化',
    dataIndex: 'balance_change',
    key: 'balance_change',
    width: 220,
  },
  {
    title: '失败原因',
    dataIndex: 'failure_reason',
    key: 'failure_reason',
    width: 260,
  },
  {
    title: '续费后到期',
    dataIndex: 'actual_expires_at',
    key: 'actual_expires_at',
    width: 180,
  },
  { title: '订单号', dataIndex: 'order_no', key: 'order_no', width: 180 },
  { title: '操作', key: 'actions', width: 100, fixed: 'right' as const },
];

const summary = computed(() => detail.value);
const dueItems = computed(() => summary.value?.due_items || []);
const futurePlanItems = computed(() => summary.value?.future_plan_items || []);
const historyItems = computed(() => summary.value?.history_items || []);
const latestFailedIps = computed(() => summary.value?.latest_failed_ips || []);
const latestFailedIpsText = computed(() => latestFailedIps.value.join('、'));
const lastRunFailures = computed(() =>
  (lastRunResult.value?.items || []).filter((item) => !item.ok),
);
const manualRunActive = computed(
  () => runningAll.value || Object.values(runningOrderIds).some(Boolean),
);
const lastRunFailureText = computed(() =>
  lastRunFailures.value
    .map((item) => `${item.ip || item.order_no}: ${item.error || '续费失败'}`)
    .join('\n'),
);
const runProgressText = computed(() => {
  const result = lastRunResult.value;
  if (!result?.run_id) return '-';
  return `${result.progress_current ?? 0} / ${result.progress_total ?? result.total ?? 0}`;
});
const expandedKeys = reactive<Record<string, boolean>>({});

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? value : [];
}

function asText(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function asNumber(value: unknown, fallback = 0) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : fallback;
}

function normalizeDueItem(
  item: Partial<DashboardAutoRenewTaskDueItem>,
  index: number,
): DashboardAutoRenewTaskDueItem {
  const orderId = Number(item.order_id || 0) || null;
  return {
    auto_renew_at: item.auto_renew_at || null,
    balance: item.balance || null,
    delete_at: item.delete_at || null,
    id: Number(item.id || orderId || index + 1),
    ip: asText(item.ip, '-'),
    ip_recycle_at: item.ip_recycle_at || null,
    last_failure_reason: item.last_failure_reason || null,
    next_run_at: item.next_run_at || null,
    order_id: orderId,
    order_no: asText(item.order_no, orderId ? `订单 ${orderId}` : '-'),
    provider: asText(item.provider),
    provider_label: asText(item.provider_label, asText(item.provider, '-')),
    queue_status: asText(item.queue_status, 'unknown'),
    queue_status_label: asText(item.queue_status_label, '-'),
    related_path: asText(
      item.related_path,
      orderId ? `/admin/cloud-orders/${orderId}` : '',
    ),
    actual_expires_at: item.actual_expires_at || null,
    status: asText(item.status),
    status_label: asText(item.status_label, '-'),
    suspend_at: item.suspend_at || null,
    tg_user_id: Number(item.tg_user_id || 0) || null,
    user_display_name: asText(item.user_display_name, '未绑定用户'),
    user_id: Number(item.user_id || 0) || null,
    username_label: asText(item.username_label, '-'),
  };
}

function normalizeHistoryItem(
  item: Partial<DashboardAutoRenewTaskHistoryItem>,
  index: number,
): DashboardAutoRenewTaskHistoryItem {
  const orderId = Number(item.order_id || 0) || null;
  return {
    balance_after: item.balance_after || null,
    balance_before: item.balance_before || null,
    balance_change: item.balance_change || null,
    batch_id: asText(item.batch_id, '-'),
    currency: asText(item.currency, 'USDT'),
    executed_at: item.executed_at || null,
    failure_reason: item.failure_reason || null,
    id: Number(item.id || orderId || index + 1),
    ip: asText(item.ip, '-'),
    is_success: Boolean(item.is_success),
    order_id: orderId,
    order_no: asText(item.order_no, orderId ? `订单 ${orderId}` : '-'),
    provider: item.provider || null,
    provider_label: asText(
      item.provider_label,
      asText(item.provider || '', '-'),
    ),
    related_path: asText(
      item.related_path,
      orderId ? `/admin/cloud-orders/${orderId}` : '',
    ),
    result_label: asText(item.result_label, item.is_success ? '成功' : '失败'),
    actual_expires_at: item.actual_expires_at || null,
    tg_user_id: Number(item.tg_user_id || 0) || null,
    user_display_name: asText(item.user_display_name, '未绑定用户'),
    user_id: Number(item.user_id || 0) || null,
    username_label: asText(item.username_label, '-'),
  };
}

function normalizeTaskDetail(value: unknown): DashboardAutoRenewTaskDetail {
  const source = (value || {}) as Partial<DashboardAutoRenewTaskDetail>;
  const due_items = asArray<Partial<DashboardAutoRenewTaskDueItem>>(
    source.due_items,
  ).map((item, index) => normalizeDueItem(item, index));
  return {
    due_count: asNumber(source.due_count, due_items.length),
    due_items,
    future_plan_items: asArray<Partial<DashboardAutoRenewTaskDueItem>>(
      source.future_plan_items,
    ).map((item, index) => normalizeDueItem(item, index)),
    history_count: asNumber(source.history_count),
    history_failure_count: asNumber(source.history_failure_count),
    history_items: asArray<Partial<DashboardAutoRenewTaskHistoryItem>>(
      source.history_items,
    ).map((item, index) => normalizeHistoryItem(item, index)),
    history_limit: asNumber(source.history_limit, historyLimit.value),
    history_offset: asNumber(source.history_offset),
    history_result: source.history_result || historyResult.value,
    history_success_count: asNumber(source.history_success_count),
    history_total_count: asNumber(source.history_total_count),
    interval_minutes: asNumber(source.interval_minutes),
    last_run_at: source.last_run_at || null,
    last_refresh_at: source.last_refresh_at || null,
    latest_batch_count: asNumber(source.latest_batch_count),
    latest_batch_failure_count: asNumber(source.latest_batch_failure_count),
    latest_batch_id: asText(source.latest_batch_id),
    latest_batch_success_count: asNumber(source.latest_batch_success_count),
    latest_failed_ips: asArray<unknown>(source.latest_failed_ips)
      .map((item) => String(item || '').trim())
      .filter(Boolean),
    next_run_at: source.next_run_at || null,
    notice_switches: source.notice_switches || [],
    recent_failure_count: asNumber(source.recent_failure_count),
    recent_success_count: asNumber(source.recent_success_count),
    refreshed: Boolean(source.refreshed),
    cache_mode: asText(source.cache_mode, 'cached'),
    active_run: source.active_run || null,
    status_label: asText(source.status_label, '置顶任务'),
    task_key: asText(source.task_key, 'auto_renew_patrol'),
    task_label: asText(source.task_label, '续费列表'),
  };
}

function isActiveRun(result?: DashboardAutoRenewRunResult | null): boolean {
  return Boolean(result && ['queued', 'running'].includes(result.status || ''));
}

function clearRunPollTimer() {
  if (runPollTimer) {
    clearTimeout(runPollTimer);
    runPollTimer = null;
  }
}

function clearRunIndicators() {
  runningAll.value = false;
  Object.keys(runningOrderIds).forEach((orderId) => {
    delete runningOrderIds[Number(orderId)];
  });
}

function applyRunIndicator(
  result: DashboardAutoRenewRunResult | null,
  active: boolean,
) {
  clearRunIndicators();
  if (!active || !result) return;
  const targetOrderId = Number(result.target_order_id || 0);
  if (result.run_kind === 'single' && targetOrderId > 0) {
    runningOrderIds[targetOrderId] = true;
    return;
  }
  runningAll.value = true;
}

function runMessageKey(result?: DashboardAutoRenewRunResult | null) {
  const targetOrderId = Number(result?.target_order_id || 0);
  return result?.run_kind === 'single' && targetOrderId > 0
    ? `renew-run-${targetOrderId}`
    : 'renew-run-all';
}

function runProgressMessage(result: DashboardAutoRenewRunResult) {
  const progress = `${result.progress_current ?? 0} / ${result.progress_total ?? result.total ?? 0}`;
  return result.run_kind === 'single'
    ? `当前服务器续费正在后台执行：${progress}`
    : `续费任务后台执行中：${progress}`;
}

function scheduleRunPoll(runId: string, delay = 1500) {
  clearRunPollTimer();
  watchedRunId = runId;
  runPollTimer = setTimeout(() => {
    void pollAutoRenewRun(runId);
  }, delay);
}

async function finishAutoRenewRun(result: DashboardAutoRenewRunResult) {
  clearRunPollTimer();
  watchedRunId = '';
  applyRunIndicator(result, false);
  lastRunResult.value = result;
  const messageKey = runMessageKey(result);
  if (result.failure_count > 0 || result.status === 'failed') {
    failurePanelOpen.value = (result.items || []).some((item) => !item.ok);
    message.error({
      content:
        result.last_error ||
        `后台执行完成：共 ${result.total} 条，成功 ${result.success_count}，失败 ${result.failure_count}`,
      key: messageKey,
    });
  } else {
    let successContent = result.message || '当前没有可执行的续费任务';
    if (result.total > 0) {
      successContent =
        result.run_kind === 'single'
          ? '当前服务器续费执行完成'
          : `后台执行完成：共 ${result.total} 条，成功 ${result.success_count}`;
    }
    message.success({
      content: successContent,
      key: messageKey,
    });
  }
  await loadData({ silent: true });
}

async function pollAutoRenewRun(runId: string) {
  if (!runId || watchedRunId !== runId) return;
  runPollTimer = null;
  try {
    const result = await getDashboardAutoRenewRunApi(runId);
    runPollFailures = 0;
    lastRunResult.value = result;
    if (isActiveRun(result)) {
      applyRunIndicator(result, true);
      message.loading({
        content: runProgressMessage(result),
        key: runMessageKey(result),
        duration: 0,
      });
      scheduleRunPoll(runId);
      return;
    }
    await finishAutoRenewRun(result);
  } catch (error: any) {
    runPollFailures += 1;
    if (runPollFailures >= 5) {
      watchedRunId = '';
      applyRunIndicator(lastRunResult.value, true);
      message.warning({
        content:
          error?.message ||
          '后台任务仍可能执行，进度查询暂时失败，请刷新页面重试',
        key: runMessageKey(lastRunResult.value),
      });
      return;
    }
    scheduleRunPoll(runId, 3000);
  }
}

function watchAutoRenewRun(result: DashboardAutoRenewRunResult) {
  const runId = result.run_id || result.batch_id;
  if (!runId || !isActiveRun(result)) return;
  lastRunResult.value = result;
  applyRunIndicator(result, true);
  runPollFailures = 0;
  if (watchedRunId !== runId || !runPollTimer) {
    scheduleRunPoll(runId, 500);
  }
}

function renewRowKey(record: DashboardAutoRenewTaskDueItem) {
  return (
    record.id ||
    record.order_id ||
    `${record.ip || '-'}-${record.order_no || '-'}-${record.queue_status || '-'}`
  );
}

function historyRowKey(record: DashboardAutoRenewTaskHistoryItem) {
  return (
    record.id ||
    `${record.batch_id || '-'}-${record.order_no || '-'}-${record.executed_at || '-'}`
  );
}

function failureRowKey(record: DashboardAutoRenewRunResultItem) {
  return `${record.order_id || record.order_no || '-'}-${record.ip || '-'}-${record.queue_status || '-'}`;
}

function isExpanded(key: string) {
  return Boolean(expandedKeys[key]);
}

function toggleExpanded(key: string) {
  expandedKeys[key] = !expandedKeys[key];
}

function shouldShowExpand(value?: null | string, threshold = 48) {
  return Boolean(value && value.length > threshold);
}

function fmtTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function fmtValue(value?: null | string) {
  return value || '-';
}

function fmtBalanceChange(item: DashboardAutoRenewTaskHistoryItem) {
  const before = item.balance_before || '-';
  const after = item.balance_after || '-';
  const delta = item.balance_change
    ? `${item.balance_change} ${item.currency}`
    : '-';
  if (!item.is_success) {
    return `${before} → ${after}`;
  }
  return `${before} → ${after}（${delta}）`;
}

function resultColor(item: DashboardAutoRenewTaskHistoryItem) {
  return item.is_success ? 'success' : 'error';
}

function queueColor(status?: string) {
  if (status === 'retry_failed') return 'error';
  if (status === 'due_now' || status === 'fallback_retry') return 'warning';
  if (status === 'within_window') return 'processing';
  return 'default';
}

async function loadData(options?: { refresh?: boolean; silent?: boolean }) {
  if (!options?.silent) {
    loading.value = true;
  }
  try {
    const normalized = normalizeTaskDetail(
      await getDashboardAutoRenewTaskDetailApi({
        history_limit: historyLimit.value,
        history_offset: (historyPage.value - 1) * historyLimit.value,
        history_result: historyResult.value,
        refresh: options?.refresh ? 1 : undefined,
      }),
    );
    detail.value = normalized;
    const activeRun = normalized.active_run;
    if (activeRun && isActiveRun(activeRun)) {
      watchAutoRenewRun(activeRun);
    } else if (manualRunActive.value || isActiveRun(lastRunResult.value)) {
      clearRunIndicators();
      if (isActiveRun(lastRunResult.value)) {
        lastRunResult.value = null;
      }
    }
    return true;
  } catch (error: any) {
    message.error(error?.message || '续费列表加载失败');
    detail.value = null;
    return false;
  } finally {
    loading.value = false;
  }
}

async function changeHistoryPage(page: number, pageSize: number) {
  const pageSizeChanged = pageSize !== historyLimit.value;
  historyPage.value = pageSizeChanged ? 1 : page;
  historyLimit.value = pageSize;
  await loadData({ silent: true });
}

async function changeHistoryResult(value: number | string) {
  historyResult.value = value as 'all' | 'failure' | 'success';
  historyPage.value = 1;
  await loadData({ silent: true });
}

async function runAllRenewals() {
  if (!requireCloudDangerPermission('执行全部续费任务')) return;
  if (manualRunActive.value) {
    return;
  }
  runningAll.value = true;
  message.loading({
    content: '正在执行全部续费任务...',
    key: 'renew-run-all',
    duration: 0,
  });
  try {
    const result = await runDashboardAutoRenewTasksApi();
    lastRunResult.value = result;
    if (isActiveRun(result)) {
      message.loading({
        content:
          result.message || `已提交 ${result.total} 条续费任务到后台执行`,
        key: 'renew-run-all',
        duration: 0,
      });
      watchAutoRenewRun(result);
      return;
    }
    await finishAutoRenewRun(result);
  } catch (error: any) {
    message.error({
      content: error?.message || '执行全部续费任务失败',
      key: 'renew-run-all',
    });
    const loaded = await loadData({ silent: true });
    if (loaded && !isActiveRun(detail.value?.active_run)) {
      clearRunIndicators();
    }
  }
}

function dueOrderId(record: DashboardAutoRenewTaskDueItem) {
  return Number(record.order_id || 0) || 0;
}

function isRenewRunning(record: DashboardAutoRenewTaskDueItem) {
  const orderId = dueOrderId(record);
  return orderId > 0 && Boolean(runningOrderIds[orderId]);
}

async function runSingleRenewal(record: DashboardAutoRenewTaskDueItem) {
  const orderId = dueOrderId(record);
  if (!requireCloudDangerPermission('执行单个服务器续费')) return;
  if (!orderId || manualRunActive.value) {
    return;
  }
  runningOrderIds[orderId] = true;
  message.loading({
    content: `正在执行 ${record.ip || record.order_no} 的续费...`,
    key: `renew-run-${orderId}`,
    duration: 0,
  });
  try {
    const result = await runDashboardAutoRenewOrderApi(orderId);
    lastRunResult.value = result;
    if (isActiveRun(result)) {
      message.loading({
        content: result.message || '已提交当前服务器续费到后台执行',
        key: `renew-run-${orderId}`,
        duration: 0,
      });
      watchAutoRenewRun(result);
      return;
    }
    await finishAutoRenewRun(result);
  } catch (error: any) {
    message.error({
      content: error?.message || '执行续费失败',
      key: `renew-run-${orderId}`,
    });
    const loaded = await loadData({ silent: true });
    if (loaded && !isActiveRun(detail.value?.active_run)) {
      runningOrderIds[orderId] = false;
    }
  }
}

function openOrder(path: string) {
  if (path) {
    router.push(path).catch(() => {});
  }
}

function goBack() {
  router.push('/admin/cloud-orders/list').catch(() => {});
}

onMounted(loadData);
onBeforeUnmount(() => {
  watchedRunId = '';
  clearRunPollTimer();
});
</script>

<template>
  <Page
    description="独立查看续费列表结果，支持一键执行全部任务与单项续费"
    title="续费列表"
  >
    <Space direction="vertical" style="width: 100%" :size="16">
      <Card :loading="loading">
        <template #title>
          <Space wrap>
            <Button size="small" @click="goBack">返回云订单</Button>
            <Button
              size="small"
              :loading="loading"
              @click="loadData({ refresh: true })"
            >
              刷新快照
            </Button>
            <Button
              type="primary"
              size="small"
              :disabled="!canRunCloudDanger || manualRunActive"
              :loading="runningAll"
              @click="runAllRenewals"
            >
              一键执行全部任务
            </Button>
            <span>{{ summary?.task_label || '续费列表' }}</span>
            <Tag color="processing">
              {{ summary?.status_label || '置顶任务' }}
            </Tag>
          </Space>
        </template>

        <Descriptions bordered :column="2" size="small">
          <Descriptions.Item label="任务名称">
            {{ summary?.task_label || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="巡检频率">
            {{
              summary?.interval_minutes
                ? `${summary.interval_minutes} 分钟`
                : '-'
            }}
          </Descriptions.Item>
          <Descriptions.Item label="下次执行">
            {{ fmtTime(summary?.next_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="上次执行">
            {{ fmtTime(summary?.last_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="快照刷新">
            {{ fmtTime(summary?.last_refresh_at) }}
            <Tag v-if="summary?.cache_mode" color="default">
              {{ summary.cache_mode === 'refreshed' ? '已刷新' : '缓存' }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="最近24小时成功">
            {{ summary?.recent_success_count ?? 0 }}
          </Descriptions.Item>
          <Descriptions.Item label="最近24小时失败">
            {{ summary?.recent_failure_count ?? 0 }}
          </Descriptions.Item>
          <Descriptions.Item label="当前待执行 IP">
            {{ summary?.due_count ?? 0 }}
          </Descriptions.Item>
          <Descriptions.Item v-if="lastRunResult?.run_id" label="手动批次状态">
            <Tag
              :color="
                manualRunActive || isActiveRun(lastRunResult)
                  ? 'processing'
                  : lastRunResult.failure_count > 0
                    ? 'error'
                    : 'success'
              "
            >
              {{ lastRunResult.status_label || lastRunResult.status || '-' }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item v-if="lastRunResult?.run_id" label="手动批次进度">
            {{ runProgressText }}
            <span v-if="lastRunResult.current_order_no">
              / {{ lastRunResult.current_order_no }}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="最新批次">
            {{ summary?.latest_batch_id || '-' }} /
            {{ summary?.latest_batch_count ?? 0 }} 条
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
          :columns="failureColumns"
          :data-source="lastRunFailures"
          :pagination="false"
          :row-key="failureRowKey"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'error'">
              <TypographyParagraph class="mb-0 break-all text-sm leading-6">
                {{ (record as DashboardAutoRenewRunResultItem).error || '-' }}
              </TypographyParagraph>
            </template>
          </template>
        </Table>
      </Card>

      <Card title="本批次执行摘要">
        <Descriptions bordered :column="2" size="small">
          <Descriptions.Item label="批次号">
            {{ summary?.latest_batch_id || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="总记录数">
            {{ summary?.latest_batch_count ?? 0 }}
          </Descriptions.Item>
          <Descriptions.Item label="成功数">
            <Tag color="success">
              {{ summary?.latest_batch_success_count ?? 0 }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="失败数">
            <Tag color="error">
              {{ summary?.latest_batch_failure_count ?? 0 }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="失败 IP" :span="2">
            <template v-if="latestFailedIps.length > 0">
              <Space wrap>
                <Tag v-for="ip in latestFailedIps" :key="ip" color="error">
                  {{ ip }}
                </Tag>
              </Space>
            </template>
            <span v-else>-</span>
          </Descriptions.Item>
        </Descriptions>
        <div
          v-if="latestFailedIpsText"
          style="margin-top: 12px; color: var(--color-error)"
        >
          <div style="margin-bottom: 4px">最新失败 IP：</div>
          <TypographyParagraph
            :content="latestFailedIpsText"
            :ellipsis="
              isExpanded('latest-failed-ips')
                ? false
                : { rows: 2, tooltip: latestFailedIpsText }
            "
            class="mb-0 break-all text-sm leading-6"
          />
          <Button
            v-if="shouldShowExpand(latestFailedIpsText, 60)"
            type="link"
            size="small"
            class="mt-1 h-auto px-0 py-0"
            @click="toggleExpanded('latest-failed-ips')"
          >
            {{ isExpanded('latest-failed-ips') ? '收起' : '展开' }}
          </Button>
        </div>
      </Card>

      <Card title="待执行 IP（含失败待重试 / 过期兜底重试）">
        <Table
          :columns="dueColumns"
          :data-source="dueItems"
          :loading="loading"
          :row-key="renewRowKey"
          :pagination="false"
          :scroll="{ x: 1320 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'queue_status_label'">
              <div>
                <Tag
                  :color="
                    queueColor(
                      (record as DashboardAutoRenewTaskDueItem).queue_status,
                    )
                  "
                >
                  {{
                    (record as DashboardAutoRenewTaskDueItem)
                      .queue_status_label || '-'
                  }}
                </Tag>
                <div
                  v-if="
                    (record as DashboardAutoRenewTaskDueItem)
                      .last_failure_reason
                  "
                  style="margin-top: 4px; color: var(--color-error)"
                >
                  <TypographyParagraph
                    :content="
                      (record as DashboardAutoRenewTaskDueItem)
                        .last_failure_reason || ''
                    "
                    :ellipsis="
                      isExpanded(
                        `due-failure-${(record as DashboardAutoRenewTaskDueItem).id}`,
                      )
                        ? false
                        : {
                            rows: 2,
                            tooltip: (record as DashboardAutoRenewTaskDueItem)
                              .last_failure_reason,
                          }
                    "
                    class="mb-0 break-all text-xs leading-5"
                  />
                  <Button
                    v-if="
                      shouldShowExpand(
                        (record as DashboardAutoRenewTaskDueItem)
                          .last_failure_reason,
                        32,
                      )
                    "
                    type="link"
                    size="small"
                    class="mt-1 h-auto px-0 py-0"
                    @click="
                      toggleExpanded(
                        `due-failure-${(record as DashboardAutoRenewTaskDueItem).id}`,
                      )
                    "
                  >
                    {{
                      isExpanded(
                        `due-failure-${(record as DashboardAutoRenewTaskDueItem).id}`,
                      )
                        ? '收起'
                        : '展开'
                    }}
                  </Button>
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'balance'">
              {{ fmtValue((record as DashboardAutoRenewTaskDueItem).balance) }}
              USDT
            </template>
            <template v-else-if="column.key === 'actual_expires_at'">
              {{
                fmtTime(
                  (record as DashboardAutoRenewTaskDueItem).actual_expires_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'auto_renew_at'">
              {{
                fmtTime((record as DashboardAutoRenewTaskDueItem).auto_renew_at)
              }}
            </template>
            <template v-else-if="column.key === 'next_run_at'">
              {{
                fmtTime((record as DashboardAutoRenewTaskDueItem).next_run_at)
              }}
            </template>
            <template v-else-if="column.key === 'plan'">
              <div>
                <div>
                  {{ (record as DashboardAutoRenewTaskDueItem).provider_label }}
                </div>
                <div style="color: var(--color-text-secondary)">
                  关机
                  {{
                    fmtValue(
                      (record as DashboardAutoRenewTaskDueItem).suspend_at,
                    )
                  }}
                </div>
                <div style="color: var(--color-text-secondary)">
                  删机
                  {{
                    fmtValue(
                      (record as DashboardAutoRenewTaskDueItem).delete_at,
                    )
                  }}
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space :size="4">
                <Button
                  type="link"
                  size="small"
                  :loading="
                    isRenewRunning(record as DashboardAutoRenewTaskDueItem)
                  "
                  :disabled="
                    !canRunCloudDanger ||
                    manualRunActive ||
                    !dueOrderId(record as DashboardAutoRenewTaskDueItem)
                  "
                  @click="
                    runSingleRenewal(record as DashboardAutoRenewTaskDueItem)
                  "
                >
                  执行续费
                </Button>
                <Button
                  type="link"
                  size="small"
                  @click="
                    openOrder(
                      (record as DashboardAutoRenewTaskDueItem).related_path,
                    )
                  "
                >
                  待执行IP详情
                </Button>
              </Space>
            </template>
          </template>
        </Table>
        <Empty
          v-if="dueItems.length === 0 && !loading"
          description="当前没有待执行的自动续费任务"
        />
      </Card>

      <Card title="未来执行计划">
        <Table
          :columns="dueColumns"
          :data-source="futurePlanItems"
          :loading="loading"
          :row-key="renewRowKey"
          :pagination="{ pageSize: 8 }"
          :scroll="{ x: 1500 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'queue_status_label'">
              <Tag
                :color="
                  queueColor(
                    (record as DashboardAutoRenewTaskDueItem).queue_status,
                  )
                "
              >
                {{
                  (record as DashboardAutoRenewTaskDueItem)
                    .queue_status_label || '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'balance'">
              {{ fmtValue((record as DashboardAutoRenewTaskDueItem).balance) }}
              USDT
            </template>
            <template v-else-if="column.key === 'actual_expires_at'">
              {{
                fmtTime(
                  (record as DashboardAutoRenewTaskDueItem).actual_expires_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'auto_renew_at'">
              {{
                fmtTime((record as DashboardAutoRenewTaskDueItem).auto_renew_at)
              }}
            </template>
            <template v-else-if="column.key === 'next_run_at'">
              {{
                fmtTime((record as DashboardAutoRenewTaskDueItem).next_run_at)
              }}
            </template>
            <template v-else-if="column.key === 'plan'">
              <div>
                <div>
                  {{ (record as DashboardAutoRenewTaskDueItem).provider_label }}
                </div>
                <div style="color: var(--color-text-secondary)">
                  关机
                  {{
                    fmtValue(
                      (record as DashboardAutoRenewTaskDueItem).suspend_at,
                    )
                  }}
                </div>
                <div style="color: var(--color-text-secondary)">
                  删机
                  {{
                    fmtValue(
                      (record as DashboardAutoRenewTaskDueItem).delete_at,
                    )
                  }}
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                type="link"
                size="small"
                @click="
                  openOrder(
                    (record as DashboardAutoRenewTaskDueItem).related_path,
                  )
                "
              >
                订单详情
              </Button>
            </template>
          </template>
        </Table>
      </Card>

      <Card title="历史执行记录">
        <template #extra>
          <Segmented
            :options="historyResultOptions"
            :value="historyResult"
            @change="changeHistoryResult"
          />
        </template>
        <Table
          :columns="historyColumns"
          :data-source="historyItems"
          :loading="loading"
          :row-key="historyRowKey"
          :pagination="{
            current: historyPage,
            pageSize: historyLimit,
            showQuickJumper: true,
            showSizeChanger: true,
            total: summary?.history_count || 0,
            onChange: changeHistoryPage,
          }"
          :scroll="{ x: 1680 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'executed_at'">
              {{
                fmtTime(
                  (record as DashboardAutoRenewTaskHistoryItem).executed_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'result_label'">
              <Tag
                :color="
                  resultColor(record as DashboardAutoRenewTaskHistoryItem)
                "
              >
                {{ (record as DashboardAutoRenewTaskHistoryItem).result_label }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'balance_change'">
              <span>{{
                fmtBalanceChange(record as DashboardAutoRenewTaskHistoryItem)
              }}</span>
            </template>
            <template v-else-if="column.key === 'actual_expires_at'">
              {{
                fmtTime(
                  (record as DashboardAutoRenewTaskHistoryItem)
                    .actual_expires_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'failure_reason'">
              <div
                v-if="
                  !(record as DashboardAutoRenewTaskHistoryItem).is_success &&
                  (record as DashboardAutoRenewTaskHistoryItem).failure_reason
                "
              >
                <Tag color="error" style="margin-bottom: 4px">失败原因</Tag>
                <TypographyParagraph
                  :content="
                    (record as DashboardAutoRenewTaskHistoryItem)
                      .failure_reason || ''
                  "
                  :ellipsis="
                    isExpanded(
                      `history-failure-${(record as DashboardAutoRenewTaskHistoryItem).id}`,
                    )
                      ? false
                      : {
                          rows: 2,
                          tooltip: (record as DashboardAutoRenewTaskHistoryItem)
                            .failure_reason,
                        }
                  "
                  class="mb-0 break-all text-xs leading-5"
                />
                <Button
                  v-if="
                    shouldShowExpand(
                      (record as DashboardAutoRenewTaskHistoryItem)
                        .failure_reason,
                      36,
                    )
                  "
                  type="link"
                  size="small"
                  class="mt-1 h-auto px-0 py-0"
                  @click="
                    toggleExpanded(
                      `history-failure-${(record as DashboardAutoRenewTaskHistoryItem).id}`,
                    )
                  "
                >
                  {{
                    isExpanded(
                      `history-failure-${(record as DashboardAutoRenewTaskHistoryItem).id}`,
                    )
                      ? '收起'
                      : '展开'
                  }}
                </Button>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                v-if="
                  (record as DashboardAutoRenewTaskHistoryItem).related_path
                "
                type="link"
                size="small"
                @click="
                  openOrder(
                    (record as DashboardAutoRenewTaskHistoryItem).related_path,
                  )
                "
              >
                订单详情
              </Button>
              <span v-else>-</span>
            </template>
          </template>
        </Table>
      </Card>
    </Space>
    <Modal
      v-model:open="failurePanelOpen"
      title="续费执行失败原因"
      width="760px"
      :footer="null"
    >
      <Alert
        type="error"
        show-icon
        :message="`失败 ${lastRunFailures.length} 条`"
        description="续费执行已完成，以下 IP 失败，需要按原因处理后重试。"
        style="margin-bottom: 12px"
      />
      <TypographyParagraph
        :copyable="lastRunFailureText ? { text: lastRunFailureText } : false"
        class="mb-3 whitespace-pre-wrap break-all text-sm leading-6"
      >
        {{ lastRunFailureText || '暂无失败原因' }}
      </TypographyParagraph>
      <Table
        :columns="failureColumns"
        :data-source="lastRunFailures"
        :pagination="false"
        :row-key="failureRowKey"
        :scroll="{ x: 900 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'error'">
            <TypographyParagraph class="mb-0 break-all text-sm leading-6">
              {{ (record as DashboardAutoRenewRunResultItem).error || '-' }}
            </TypographyParagraph>
          </template>
        </template>
      </Table>
    </Modal>
  </Page>
</template>
