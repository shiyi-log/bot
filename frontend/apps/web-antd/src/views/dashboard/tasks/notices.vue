<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardNoticePlanDetail,
  DashboardNoticePlanHistoryItem,
  DashboardNoticeUserSummaryItem,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Descriptions,
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
  deleteDashboardNoticeHistoryApi,
  getDashboardNoticePlanApi,
  refreshDashboardNoticePlanApi,
  updateDashboardNoticePlanTextApi,
  updateDashboardNoticeSwitchesApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const loading = ref(false);
const refreshingNoticePlan = ref(false);
const detail = ref<DashboardNoticePlanDetail | null>(null);
const textModalOpen = ref(false);
const textSaving = ref(false);
const deletingHistoryIds = ref<Record<string, boolean>>({});
const textValue = ref('');
const textTarget = ref<DashboardNoticeUserSummaryItem | null>(null);
const expandedTextKeys = ref<Record<string, boolean>>({});
const switchSaving = ref<Record<string, boolean>>({});
const noticePage = ref(1);
const noticeLimit = ref(10);
const historyPage = ref(1);
const historyLimit = ref(10);
const visibleColumnState = reactive<Record<string, boolean>>({});

const fieldSwitchItems = [
  { key: 'created_at', label: '发送时间' },
  { key: 'user_display_name', label: '用户' },
  { key: 'notice_type_label', label: '通知类型' },
  { key: 'notice_status_label', label: '通知状态' },
  { key: 'plan_scope_label', label: '计划范围' },
  { key: 'ips', label: 'IP列表' },
  { key: 'ip_count', label: 'IP数量' },
  { key: 'next_notice_at', label: '通知时间' },
  { key: 'text', label: '通知文案' },
  { key: 'channels', label: '通知渠道' },
  { key: 'retry', label: '重试说明' },
  { key: 'actions', label: '操作' },
] as const;

fieldSwitchItems.forEach((item) => {
  visibleColumnState[item.key] = !['channels', 'ips', 'retry', 'text'].includes(
    item.key,
  );
});

const noticeBatchColumnsAll: TableColumnsType<DashboardNoticeUserSummaryItem> =
  [
    {
      title: '用户',
      dataIndex: 'user_display_name',
      key: 'user_display_name',
      width: 180,
    },
    {
      title: '通知类型',
      dataIndex: 'notice_type_label',
      key: 'notice_type_label',
      width: 150,
    },
    {
      title: '计划范围',
      dataIndex: 'plan_scope_label',
      key: 'plan_scope_label',
      width: 110,
    },
    {
      title: '通知渠道',
      dataIndex: 'notice_channel_label',
      key: 'notice_channel_label',
      width: 210,
    },
    { title: 'IP数量', dataIndex: 'ip_count', key: 'ip_count', width: 90 },
    { title: 'IP列表', dataIndex: 'ips', key: 'ips', width: 340 },
    {
      title: '通知文案',
      dataIndex: 'notice_text_preview',
      key: 'notice_text_preview',
      width: 460,
    },
    {
      title: '通知时间',
      dataIndex: 'next_notice_at',
      key: 'next_notice_at',
      width: 180,
    },
    {
      title: '失败重试',
      dataIndex: 'failed_retry_count',
      key: 'failed_retry_count',
      width: 100,
    },
    { title: '操作', key: 'actions', width: 100, fixed: 'right' },
  ];

const historyColumnsAll: TableColumnsType<DashboardNoticePlanHistoryItem> = [
  { title: '发送时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  {
    title: '通知类型',
    dataIndex: 'notice_type_label',
    key: 'notice_type_label',
    width: 150,
  },
  {
    title: '通知状态',
    dataIndex: 'notice_status_label',
    key: 'notice_status_label',
    width: 170,
  },
  {
    title: '通知渠道',
    dataIndex: 'notice_channel_label',
    key: 'notice_channel_label',
    width: 210,
  },
  {
    title: '用户',
    dataIndex: 'user_display_name',
    key: 'user_display_name',
    width: 160,
  },
  { title: 'IP数量', dataIndex: 'ip_count', key: 'ip_count', width: 90 },
  { title: 'IP列表', dataIndex: 'ips', key: 'ips', width: 320 },
  {
    title: '通知文案',
    dataIndex: 'notice_text_preview',
    key: 'notice_text_preview',
    width: 500,
  },
  {
    title: '重试说明',
    dataIndex: 'retry_label',
    key: 'retry_label',
    width: 300,
  },
  { title: '操作', key: 'actions', width: 100, fixed: 'right' },
];

function filterNoticeColumns<T>(columns: TableColumnsType<T>) {
  return columns.filter((column) => {
    const key = String(column.key || '');
    if (key === 'ips') return visibleColumnState.ips;
    if (key === 'notice_text_preview') return visibleColumnState.text;
    if (key === 'notice_channel_label') return visibleColumnState.channels;
    if (['failed_retry_count', 'retry_label'].includes(key)) {
      return visibleColumnState.retry;
    }
    return visibleColumnState[key] !== false;
  });
}

const noticeBatchColumns = computed(() =>
  filterNoticeColumns(noticeBatchColumnsAll),
);
const historyColumns = computed(() => filterNoticeColumns(historyColumnsAll));
const visibleFieldState = computed(() => ({
  channels: visibleColumnState.channels !== false,
  ips: visibleColumnState.ips !== false,
  retry: visibleColumnState.retry !== false,
  text: visibleColumnState.text !== false,
}));
const noticeFields = computed(() =>
  [
    'basic',
    visibleFieldState.value.ips ? 'ips' : '',
    visibleFieldState.value.text ? 'text' : '',
    visibleFieldState.value.channels ? 'channels' : '',
    visibleFieldState.value.retry ? 'retry' : '',
    visibleColumnState.actions === false ? '' : 'actions',
  ]
    .filter(Boolean)
    .join(','),
);
const noticeTableScroll = computed(() => ({
  x:
    910 +
    (visibleFieldState.value.ips ? 340 : 0) +
    (visibleFieldState.value.text ? 460 : 0) +
    (visibleFieldState.value.channels ? 210 : 0) +
    (visibleFieldState.value.retry ? 100 : 0),
}));
const historyTableScroll = computed(() => ({
  x:
    950 +
    (visibleFieldState.value.ips ? 320 : 0) +
    (visibleFieldState.value.text ? 500 : 0) +
    (visibleFieldState.value.channels ? 210 : 0) +
    (visibleFieldState.value.retry ? 300 : 0),
}));

const dueBatchItems = computed(
  () => detail.value?.active_user_summary_items || [],
);
const historyItems = computed(() => detail.value?.history_items || []);

function fmtTime(value?: null | string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}

function noticeColor(type?: string) {
  if (type === 'renew_notice' || type === 'renew_notice_batch') return 'blue';
  if (type === 'auto_renew_notice') return 'purple';
  if (type === 'delete_notice') return 'orange';
  if (type === 'recycle_notice') return 'cyan';
  return 'default';
}

function statusColor(status?: string) {
  if (status === 'sent') return 'success';
  if (status === 'failed_retry') return 'error';
  if (status === 'pending') return 'warning';
  if (status === 'scheduled_soon') return 'processing';
  return 'default';
}

function channelColor(channel?: string) {
  if (channel === 'unbound') return 'error';
  if (channel === 'telegram_fallback') return 'orange';
  if (channel === 'telegram_account') return 'purple';
  if (channel === 'telegram_chat') return 'cyan';
  return 'blue';
}

function attemptColor(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'pending') return 'processing';
  return 'default';
}

function batchRowKey(record: DashboardNoticeUserSummaryItem) {
  return record.id;
}

function historyRowKey(record: DashboardNoticePlanHistoryItem) {
  return record.id;
}

function displayUser(record: {
  user_display_name?: string;
  username_label?: string;
}) {
  const name = record.user_display_name || '未绑定用户';
  const username =
    record.username_label && record.username_label !== '-'
      ? record.username_label
      : '';
  return username ? `${name} ${username}` : name;
}

function ipListText(record: { ip?: string; ips?: string[] }) {
  const ips = Array.isArray(record.ips) ? record.ips : [];
  return ips.length > 0 ? ips.join('\n') : record.ip || '-';
}

function openOrder(path?: string) {
  if (!path) return;
  router.push(path).catch(() => {});
}

async function loadData() {
  loading.value = true;
  try {
    detail.value = await getDashboardNoticePlanApi({
      compact: 1,
      fields: noticeFields.value,
      history_limit: historyLimit.value,
      history_offset: (historyPage.value - 1) * historyLimit.value,
      limit: noticeLimit.value,
      offset: (noticePage.value - 1) * noticeLimit.value,
    });
  } catch (error: any) {
    message.error(error?.message || '通知计划加载失败');
  } finally {
    loading.value = false;
  }
}

async function toggleVisibleField(key: string, checked: boolean) {
  visibleColumnState[key] = checked;
  await loadData();
}

async function changeNoticePage(page: number, pageSize: number) {
  noticePage.value = page;
  noticeLimit.value = pageSize;
  await loadData();
}

async function changeHistoryPage(page: number, pageSize: number) {
  historyPage.value = page;
  historyLimit.value = pageSize;
  await loadData();
}

async function refreshNoticePlan() {
  refreshingNoticePlan.value = true;
  try {
    const result = await refreshDashboardNoticePlanApi({
      limit: noticeLimit.value,
      history_limit: historyLimit.value,
    });
    message.success(
      `通知计划已刷新：近期 ${result.due_count} 个 IP / 未来 ${result.future_count} 个 IP`,
    );
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '刷新通知计划失败');
  } finally {
    refreshingNoticePlan.value = false;
  }
}

function noticeTextRows(record: { ip_count?: number; ips?: string[] }) {
  const count = Number(record.ip_count || record.ips?.length || 1);
  return Math.min(Math.max(count * 3, 3), 12);
}

function noticeTextKey(record: {
  id?: number | string;
  notice_event?: string;
  notice_type?: string;
}) {
  return `${record.notice_event || record.notice_type || 'notice'}-${record.id || ''}`;
}

function isNoticeTextExpanded(record: {
  id?: number | string;
  notice_event?: string;
  notice_type?: string;
}) {
  return !!expandedTextKeys.value[noticeTextKey(record)];
}

function toggleNoticeText(record: {
  id?: number | string;
  notice_event?: string;
  notice_type?: string;
}) {
  const key = noticeTextKey(record);
  expandedTextKeys.value = {
    ...expandedTextKeys.value,
    [key]: !expandedTextKeys.value[key],
  };
}

function noticeTextStyle(record: {
  id?: number | string;
  ip_count?: number;
  ips?: string[];
  notice_event?: string;
  notice_type?: string;
}) {
  if (isNoticeTextExpanded(record)) return {};
  return {
    maxHeight: `${noticeTextRows(record) * 24}px`,
    overflow: 'hidden',
  };
}

function openTextEditor(record: DashboardNoticeUserSummaryItem) {
  if (!requireCloudDangerPermission('编辑通知文案')) return;
  textTarget.value = record;
  textValue.value = record.notice_text_preview || '';
  textModalOpen.value = true;
}

async function saveNoticeText() {
  if (!textTarget.value) return;
  if (!requireCloudDangerPermission('保存通知文案')) return;
  textSaving.value = true;
  try {
    await updateDashboardNoticePlanTextApi({
      event: textTarget.value.notice_event,
      notice_text: textValue.value,
      order_ids: textTarget.value.order_ids || [],
      user_id: textTarget.value.user_id,
    });
    message.success('通知文案已保存，后续发送会使用人工干预文案');
    textModalOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '通知文案保存失败');
  } finally {
    textSaving.value = false;
  }
}

async function updateNoticeSwitch(key: string, enabled: boolean) {
  if (!requireCloudDangerPermission('修改通知开关')) {
    await loadData();
    return;
  }
  const switches = detail.value?.notice_switches || [];
  switchSaving.value = { ...switchSaving.value, [key]: true };
  try {
    const response = await updateDashboardNoticeSwitchesApi({
      switches: [{ enabled, key }],
    });
    if (detail.value) {
      detail.value.notice_switches = response.notice_switches;
    }
    message.success(enabled ? '通知已开启' : '通知已关闭');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '通知开关保存失败');
    if (detail.value) {
      detail.value.notice_switches = switches;
    }
  } finally {
    switchSaving.value = { ...switchSaving.value, [key]: false };
  }
}

async function deleteHistory(record: DashboardNoticePlanHistoryItem) {
  if (!requireCloudDangerPermission('删除通知历史')) return;
  const id = String(record.id || '');
  if (!id || deletingHistoryIds.value[id]) return;
  deletingHistoryIds.value = { ...deletingHistoryIds.value, [id]: true };
  try {
    const result = await deleteDashboardNoticeHistoryApi(id);
    message.success(
      `历史通知已删除，已重置 ${result.reset_count || 0} 个订单通知状态`,
    );
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '删除历史通知失败');
  } finally {
    deletingHistoryIds.value = { ...deletingHistoryIds.value, [id]: false };
  }
}

function resetNoticeText() {
  textValue.value = '';
}

function goTasks() {
  router.push('/admin/tasks').catch(() => {});
}

onMounted(loadData);
</script>

<template>
  <Page
    description="按用户和月份整合通知计划；同一用户每月只生成一条合并文案"
    title="通知计划"
  >
    <Space direction="vertical" style="width: 100%" :size="16">
      <Card :loading="loading">
        <template #title>
          <Space wrap>
            <Button size="small" @click="goTasks">返回任务列表</Button>
            <Button size="small" :loading="loading" @click="loadData">
              刷新
            </Button>
            <Button
              size="small"
              :loading="refreshingNoticePlan"
              @click="refreshNoticePlan"
            >
              刷新计划表
            </Button>
            <span>{{ detail?.task_label || '通知计划' }}</span>
            <Tag color="processing">
              {{ detail?.status_label || '置顶任务' }}
            </Tag>
            <Tag :color="refreshingNoticePlan ? 'warning' : 'default'">
              {{
                refreshingNoticePlan
                  ? '计划表刷新中'
                  : `最后刷新：${fmtTime(detail?.last_refresh_at)}`
              }}
            </Tag>
          </Space>
        </template>

        <Alert
          type="info"
          show-icon
          :message="`当前每页显示 ${noticeLimit} 组通知计划 / ${historyLimit} 条历史，支持翻页，并压缩长文案预览。`"
          style="margin-bottom: 12px"
        />
        <div class="notice-field-switches">
          <span class="notice-field-switch-label">显示列：</span>
          <Space wrap>
            <Tag
              v-for="item in fieldSwitchItems"
              :key="item.key"
              :color="visibleColumnState[item.key] ? 'processing' : 'default'"
              class="notice-field-switch-tag"
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
          <Descriptions.Item label="任务名称">
            {{ detail?.task_label || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="巡检频率">
            {{
              detail?.interval_minutes ? `${detail.interval_minutes} 分钟` : '-'
            }}
          </Descriptions.Item>
          <Descriptions.Item label="下次巡检">
            {{ fmtTime(detail?.next_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="上次通知">
            {{ fmtTime(detail?.last_run_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="计划表最后刷新">
            {{ fmtTime(detail?.last_refresh_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="刷新状态">
            <Tag :color="refreshingNoticePlan ? 'warning' : 'success'">
              {{ refreshingNoticePlan ? '刷新中' : '空闲' }}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="最近24小时送达">
            <Tag color="success">
              {{ detail?.recent_success_user_count ?? 0 }} 用户
            </Tag>
            / {{ detail?.recent_success_count ?? 0 }} 条
          </Descriptions.Item>
          <Descriptions.Item label="最近24小时失败">
            <Tag color="error">
              {{ detail?.recent_failure_user_count ?? 0 }} 用户
            </Tag>
            / {{ detail?.recent_failure_count ?? 0 }} 条
          </Descriptions.Item>
          <Descriptions.Item label="通知计划">
            <Tag color="processing">
              {{ detail?.active_user_count ?? 0 }} 组用户通知
            </Tag>
            / {{ (detail?.due_count ?? 0) + (detail?.future_count ?? 0) }}
            个 IP 通知项
          </Descriptions.Item>
          <Descriptions.Item label="近期计划">
            <Tag color="warning">
              {{ detail?.due_user_count ?? 0 }} 组用户通知
            </Tag>
            / {{ detail?.due_count ?? 0 }} 个 IP 通知项
          </Descriptions.Item>
          <Descriptions.Item label="未来计划">
            <Tag color="processing">
              {{ detail?.future_user_count ?? 0 }} 组用户通知
            </Tag>
            / {{ detail?.future_count ?? 0 }} 个 IP 通知项
          </Descriptions.Item>
        </Descriptions>
        <div
          v-if="detail?.notice_switches?.length"
          class="mt-3 flex flex-wrap items-center gap-3"
        >
          <span class="text-sm text-gray-500">通知开关：</span>
          <Space wrap>
            <Tag
              v-for="item in detail.notice_switches"
              :key="item.key"
              :color="item.enabled ? 'success' : 'default'"
              class="flex items-center gap-2 px-2 py-1"
            >
              <span>{{ item.label }}</span>
              <Switch
                size="small"
                :checked="item.enabled"
                :disabled="!canRunCloudDanger"
                :loading="switchSaving[item.key]"
                @change="
                  (checked) => updateNoticeSwitch(item.key, checked as boolean)
                "
              />
            </Tag>
          </Space>
        </div>
        <Alert
          v-if="detail?.retry_policy_label"
          type="info"
          show-icon
          :message="detail.retry_policy_label"
          style="margin-top: 12px"
        />
      </Card>

      <Card title="通知计划（按用户显示）">
        <Table
          :columns="noticeBatchColumns"
          :data-source="dueBatchItems"
          :loading="loading"
          :pagination="{
            current: noticePage,
            pageSize: noticeLimit,
            showQuickJumper: true,
            showSizeChanger: true,
            total: detail?.active_user_count || 0,
            onChange: changeNoticePage,
          }"
          :row-key="batchRowKey"
          :scroll="noticeTableScroll"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user_display_name'">
              {{ displayUser(record as DashboardNoticeUserSummaryItem) }}
            </template>
            <template v-else-if="column.key === 'notice_type_label'">
              <Tag
                :color="
                  noticeColor(
                    (record as DashboardNoticeUserSummaryItem).notice_type,
                  )
                "
              >
                {{
                  (record as DashboardNoticeUserSummaryItem).notice_type_label
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'plan_scope_label'">
              <Tag
                :color="
                  (record as DashboardNoticeUserSummaryItem).plan_scope ===
                  'future'
                    ? 'processing'
                    : 'warning'
                "
              >
                {{
                  (record as DashboardNoticeUserSummaryItem).plan_scope_label ||
                  '-'
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'notice_channel_label'">
              <div class="flex flex-wrap gap-1">
                <Tag
                  :color="
                    channelColor(
                      (record as DashboardNoticeUserSummaryItem).notice_channel,
                    )
                  "
                >
                  {{
                    (record as DashboardNoticeUserSummaryItem)
                      .notice_channel_label || '-'
                  }}
                </Tag>
                <Tag
                  v-for="attempt in (record as DashboardNoticeUserSummaryItem)
                    .notice_channel_attempts || []"
                  :key="`${attempt.channel}-${attempt.account_id || attempt.label}`"
                  :color="attemptColor(attempt.status)"
                >
                  {{ attempt.label }}：{{ attempt.status_label }}
                </Tag>
              </div>
            </template>
            <template v-else-if="column.key === 'ips'">
              <TypographyParagraph
                :content="ipListText(record as DashboardNoticeUserSummaryItem)"
                :ellipsis="{
                  rows: 2,
                  tooltip: ipListText(record as DashboardNoticeUserSummaryItem),
                }"
                class="mb-0 whitespace-pre-line break-all text-sm leading-6"
              />
            </template>
            <template v-else-if="column.key === 'notice_text_preview'">
              <div>
                <Tag
                  v-if="
                    (record as DashboardNoticeUserSummaryItem)
                      .notice_has_manual_text
                  "
                  color="warning"
                >
                  人工干预
                </Tag>
                <div
                  class="whitespace-pre-wrap break-all text-sm leading-6"
                  :style="
                    noticeTextStyle(record as DashboardNoticeUserSummaryItem)
                  "
                  :title="
                    (record as DashboardNoticeUserSummaryItem)
                      .notice_text_preview || '-'
                  "
                >
                  {{
                    (record as DashboardNoticeUserSummaryItem)
                      .notice_text_preview || '-'
                  }}
                </div>
                <Space size="small">
                  <Button
                    v-if="visibleColumnState.text"
                    type="link"
                    size="small"
                    :disabled="!canRunCloudDanger"
                    class="h-auto px-0 py-0"
                    @click="
                      toggleNoticeText(record as DashboardNoticeUserSummaryItem)
                    "
                  >
                    {{
                      isNoticeTextExpanded(
                        record as DashboardNoticeUserSummaryItem,
                      )
                        ? '收起'
                        : '展开'
                    }}
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    :disabled="!canRunCloudDanger"
                    class="h-auto px-0 py-0"
                    @click="
                      openTextEditor(record as DashboardNoticeUserSummaryItem)
                    "
                  >
                    编辑文案
                  </Button>
                </Space>
              </div>
            </template>
            <template v-else-if="column.key === 'next_notice_at'">
              {{
                fmtTime(
                  (record as DashboardNoticeUserSummaryItem).next_notice_at,
                )
              }}
            </template>
            <template v-else-if="column.key === 'failed_retry_count'">
              <Tag
                :color="
                  (record as DashboardNoticeUserSummaryItem)
                    .failed_retry_count > 0
                    ? 'error'
                    : 'default'
                "
              >
                {{
                  (record as DashboardNoticeUserSummaryItem).failed_retry_count
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                type="link"
                size="small"
                @click="
                  openOrder(
                    (record as DashboardNoticeUserSummaryItem).related_path,
                  )
                "
              >
                订单详情
              </Button>
            </template>
          </template>
        </Table>
      </Card>

      <Card title="历史通知（按实际发送批次整合）">
        <Table
          :columns="historyColumns"
          :data-source="historyItems"
          :loading="loading"
          :pagination="{
            current: historyPage,
            pageSize: historyLimit,
            showQuickJumper: true,
            showSizeChanger: true,
            total: detail?.history_count || 0,
            onChange: changeHistoryPage,
          }"
          :row-key="historyRowKey"
          :scroll="historyTableScroll"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user_display_name'">
              {{ displayUser(record as DashboardNoticePlanHistoryItem) }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{
                fmtTime((record as DashboardNoticePlanHistoryItem).created_at)
              }}
            </template>
            <template v-else-if="column.key === 'notice_type_label'">
              <Tag
                :color="
                  noticeColor(
                    (record as DashboardNoticePlanHistoryItem).notice_type,
                  )
                "
              >
                {{
                  (record as DashboardNoticePlanHistoryItem).notice_type_label
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'notice_status_label'">
              <Tag
                :color="
                  statusColor(
                    (record as DashboardNoticePlanHistoryItem).notice_status,
                  )
                "
              >
                {{
                  (record as DashboardNoticePlanHistoryItem).notice_status_label
                }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'notice_channel_label'">
              <div class="flex flex-wrap gap-1">
                <Tag
                  :color="
                    channelColor(
                      (record as DashboardNoticePlanHistoryItem).notice_channel,
                    )
                  "
                >
                  {{
                    (record as DashboardNoticePlanHistoryItem)
                      .notice_channel_label || '-'
                  }}
                </Tag>
                <Tag
                  v-for="attempt in (record as DashboardNoticePlanHistoryItem)
                    .notice_channel_attempts || []"
                  :key="`${attempt.channel}-${attempt.account_id || attempt.label}`"
                  :color="attemptColor(attempt.status)"
                >
                  {{ attempt.label }}：{{ attempt.status_label }}
                </Tag>
              </div>
            </template>
            <template v-else-if="column.key === 'ips'">
              <TypographyParagraph
                :content="ipListText(record as DashboardNoticePlanHistoryItem)"
                :ellipsis="{
                  rows: 2,
                  tooltip: ipListText(record as DashboardNoticePlanHistoryItem),
                }"
                class="mb-0 whitespace-pre-line break-all text-sm leading-6"
              />
            </template>
            <template v-else-if="column.key === 'notice_text_preview'">
              <div>
                <div
                  class="whitespace-pre-wrap break-all text-sm leading-6"
                  :style="
                    noticeTextStyle(record as DashboardNoticePlanHistoryItem)
                  "
                  :title="
                    (record as DashboardNoticePlanHistoryItem)
                      .notice_text_preview || '-'
                  "
                >
                  {{
                    (record as DashboardNoticePlanHistoryItem)
                      .notice_text_preview || '-'
                  }}
                </div>
                <Button
                  type="link"
                  size="small"
                  class="h-auto px-0 py-0"
                  @click="
                    toggleNoticeText(record as DashboardNoticePlanHistoryItem)
                  "
                >
                  {{
                    isNoticeTextExpanded(
                      record as DashboardNoticePlanHistoryItem,
                    )
                      ? '收起'
                      : '展开'
                  }}
                </Button>
              </div>
            </template>
            <template v-else-if="column.key === 'retry_label'">
              <TypographyParagraph
                :content="String((record as any)[column.key] || '-')"
                :ellipsis="{
                  rows: 2,
                  tooltip: String((record as any)[column.key] || '-'),
                }"
                class="mb-0 whitespace-pre-line break-all text-sm leading-6"
              />
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space size="small">
                <Button
                  type="link"
                  size="small"
                  @click="
                    openOrder(
                      (record as DashboardNoticePlanHistoryItem).related_path,
                    )
                  "
                >
                  订单详情
                </Button>
                <Button
                  danger
                  type="link"
                  size="small"
                  :disabled="!canRunCloudDanger"
                  :loading="
                    deletingHistoryIds[
                      String((record as DashboardNoticePlanHistoryItem).id)
                    ]
                  "
                  @click="
                    deleteHistory(record as DashboardNoticePlanHistoryItem)
                  "
                >
                  删除
                </Button>
              </Space>
            </template>
          </template>
        </Table>
      </Card>
    </Space>
    <Modal
      v-model:open="textModalOpen"
      title="人工干预通知文案"
      :confirm-loading="textSaving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      width="760px"
      ok-text="保存"
      @ok="saveNoticeText"
    >
      <Alert
        type="warning"
        show-icon
        message="保存后，后续实际发送给用户的通知会使用这里的文案；清空并保存可恢复系统自动文案。"
        style="margin-bottom: 12px"
      />
      <Input.TextArea
        v-model:value="textValue"
        :auto-size="{ minRows: 10, maxRows: 18 }"
        placeholder="请输入实际发给用户的通知文案"
      />
      <Button type="link" class="mt-2 px-0" @click="resetNoticeText">
        清空并恢复系统文案
      </Button>
    </Modal>
  </Page>
</template>

<style scoped>
.notice-field-switches {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.notice-field-switch-label {
  font-size: 13px;
  color: var(--ant-color-text-secondary);
  white-space: nowrap;
}

.notice-field-switch-tag {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 4px 8px;
}
</style>
