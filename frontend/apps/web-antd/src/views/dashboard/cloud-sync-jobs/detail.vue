<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudAssetSyncJob,
  DashboardCloudAssetSyncJobEvent,
  DashboardCloudAssetSyncTask,
} from '#/api/admin';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  Empty,
  message,
  Popconfirm,
  Space,
  Table,
  Tag,
  TypographyParagraph,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  cancelDashboardCloudAssetSyncJobApi,
  getDashboardCloudAssetSyncJobApi,
  retryDashboardCloudAssetSyncJobApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const route = useRoute();
const router = useRouter();
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const loading = ref(false);
const cancelling = ref(false);
const retrying = ref(false);
const job = ref<DashboardCloudAssetSyncJob | null>(null);
let pollTimer: null | ReturnType<typeof setInterval> = null;

const jobId = computed(() => Number(route.params.id || 0));
const tasks = computed<DashboardCloudAssetSyncTask[]>(
  () => job.value?.tasks || job.value?.result?.tasks || [],
);
const skippedTasks = computed<DashboardCloudAssetSyncTask[]>(
  () => job.value?.skipped_tasks || job.value?.result?.skipped_tasks || [],
);
const events = computed<DashboardCloudAssetSyncJobEvent[]>(
  () => job.value?.events || [],
);

const eventColumns = computed<TableColumnsType<DashboardCloudAssetSyncJobEvent>>(
  () => [
    { dataIndex: 'created_at', key: 'created_at', title: '时间', width: 170 },
    { dataIndex: 'event_type', key: 'event_type', title: '类型', width: 120 },
    { dataIndex: 'message', key: 'message', title: '消息', width: 260 },
    { dataIndex: 'worker_id', key: 'worker_id', title: 'Worker', width: 120 },
    { dataIndex: 'payload', key: 'payload', title: '载荷' },
  ],
);

function empty(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function formatTime(value?: null | string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}

function formatSeconds(seconds?: number) {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) return '-';
  if (value >= 3600) return `${(value / 3600).toFixed(1)}h`;
  if (value >= 60) return `${(value / 60).toFixed(1)}m`;
  return `${Math.round(value)}s`;
}

function statusColor(status?: string) {
  if (status === 'succeeded') return 'green';
  if (status === 'failed') return 'red';
  if (status === 'partial') return 'orange';
  if (status === 'running') return 'processing';
  if (status === 'queued') return 'blue';
  return 'default';
}

function eventColor(eventType?: string) {
  if (eventType === 'error') return 'red';
  if (eventType === 'warning' || eventType === 'cancel') return 'orange';
  if (eventType === 'progress' || eventType === 'task') return 'blue';
  if (eventType === 'claimed' || eventType === 'heartbeat') return 'cyan';
  if (eventType === 'retry') return 'purple';
  return 'default';
}

function scopeLabel(item: DashboardCloudAssetSyncJob | null) {
  if (!item) return '-';
  const scope = item.scope || {};
  const providers = (item.providers?.length ? item.providers : scope.providers)
    ?.join?.(' / ') || 'all';
  const regions = [scope.aliyun_region, scope.aws_region]
    .filter(Boolean)
    .join(' / ');
  const assets = item.asset_ids?.length ? `${item.asset_ids.length} 条代理` : '';
  const accounts = item.account_ids?.length
    ? `${item.account_ids.length} 个账号`
    : '';
  return [providers, assets, accounts, regions].filter(Boolean).join(' · ');
}

function compactJson(value: unknown) {
  if (!value || (typeof value === 'object' && Object.keys(value).length === 0)) {
    return '';
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function taskKey(task: DashboardCloudAssetSyncTask, index: number) {
  return `${task.provider || '-'}-${task.region || 'all'}-${task.command || '-'}-${index}`;
}

async function loadJob(showLoading = true) {
  if (!jobId.value) {
    message.error('同步任务 ID 无效');
    return;
  }
  if (showLoading) loading.value = true;
  try {
    job.value = await getDashboardCloudAssetSyncJobApi(jobId.value);
    if (job.value?.is_terminal) {
      stopPolling();
    } else {
      startPolling();
    }
  } catch (error: any) {
    message.error(error?.message || '加载同步任务失败');
  } finally {
    if (showLoading) loading.value = false;
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(() => {
    void loadJob(false);
  }, 3000);
}

function stopPolling() {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
}

async function cancelJob() {
  if (!job.value || !requireCloudDangerPermission('取消同步任务')) return;
  cancelling.value = true;
  try {
    const result = await cancelDashboardCloudAssetSyncJobApi(job.value.id);
    if (result.job) job.value = result.job;
    message.success(result.message || '取消请求已提交');
    await loadJob(false);
  } catch (error: any) {
    message.error(error?.message || '取消同步任务失败');
  } finally {
    cancelling.value = false;
  }
}

async function retryJob() {
  if (!job.value || !requireCloudDangerPermission('重试同步任务')) return;
  retrying.value = true;
  try {
    const result = await retryDashboardCloudAssetSyncJobApi(job.value.id);
    message.success('同步任务已重新入队');
    if (result.job_id) {
      router.push(`/admin/cloud-sync-jobs/${result.job_id}`).catch(() => {});
      return;
    }
    await loadJob(false);
  } catch (error: any) {
    message.error(error?.message || '重试同步任务失败');
  } finally {
    retrying.value = false;
  }
}

onMounted(() => {
  void loadJob();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <Page auto-content-height>
    <Card :loading="loading" class="mb-3" title="同步任务详情">
      <template #extra>
        <Space wrap>
          <Button size="small" @click="router.push('/admin/cloud-assets')">
            返回代理列表
          </Button>
          <Button size="small" :loading="loading" @click="loadJob()">
            刷新
          </Button>
          <Popconfirm
            title="确认取消这个同步任务？运行中的任务会在当前子任务结束后停止。"
            @confirm="cancelJob"
          >
            <Button
              danger
              size="small"
              :disabled="!job?.can_cancel || !canRunCloudDanger"
              :loading="cancelling"
            >
              取消
            </Button>
          </Popconfirm>
          <Button
            size="small"
            :disabled="!job?.is_terminal || !canRunCloudDanger"
            :loading="retrying"
            @click="retryJob"
          >
            重试
          </Button>
        </Space>
      </template>

      <Empty v-if="!loading && !job" description="暂无同步任务" />
      <Descriptions v-else bordered size="small" :column="2">
        <Descriptions.Item label="任务">
          <Space wrap>
            <span class="font-mono">#{{ job?.id || jobId }}</span>
            <Tag :color="statusColor(job?.status)">
              {{ job?.status_label || job?.status || '-' }}
            </Tag>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="Run ID">
          <TypographyParagraph
            class="!mb-0 break-all font-mono"
            :copyable="job?.run_id ? { text: job.run_id } : false"
          >
            {{ empty(job?.run_id) }}
          </TypographyParagraph>
        </Descriptions.Item>
        <Descriptions.Item label="范围">
          {{ scopeLabel(job) }}
        </Descriptions.Item>
        <Descriptions.Item label="进度">
          {{ job?.progress_current || 0 }}/{{ job?.progress_total || 0 }}
          <Tag color="blue">{{ job?.progress_percent || 0 }}%</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Worker">
          {{ empty(job?.worker_id) }} / 心跳 {{ formatTime(job?.worker_heartbeat_at) }}
        </Descriptions.Item>
        <Descriptions.Item label="时间">
          创建 {{ formatTime(job?.created_at) }} / 完成
          {{ formatTime(job?.finished_at) }}
        </Descriptions.Item>
        <Descriptions.Item label="当前任务" :span="2">
          {{ empty(job?.current_task) }}
        </Descriptions.Item>
      </Descriptions>
    </Card>

    <Card class="mb-3" title="执行结果">
      <Space class="mb-3" wrap>
        <Tag
          v-for="(task, index) in tasks"
          :key="taskKey(task, index)"
          color="cyan"
        >
          {{ task.provider || '-' }} / {{ task.region || 'all' }} /
          {{ formatSeconds(task.duration_seconds) }}
        </Tag>
        <Tag
          v-for="(task, index) in skippedTasks"
          :key="`skip-${taskKey(task, index)}`"
          color="warning"
        >
          跳过 {{ task.provider || '-' }} / {{ task.region || 'all' }}
        </Tag>
      </Space>
      <TypographyParagraph
        v-if="(job?.errors || []).length > 0 || (job?.warnings || []).length > 0"
        class="!mb-3 whitespace-pre-wrap break-all text-xs leading-5"
      >
        {{ [...(job?.errors || []), ...(job?.warnings || [])].join('\n') }}
      </TypographyParagraph>
      <TypographyParagraph
        v-if="(job?.logs || []).length > 0"
        class="!mb-0 whitespace-pre-wrap break-all font-mono text-xs leading-5"
        :ellipsis="{ rows: 12, expandable: true, symbol: '展开日志' }"
      >
        {{ (job?.logs || []).join('\n') }}
      </TypographyParagraph>
      <Empty
        v-if="
          tasks.length === 0 &&
          skippedTasks.length === 0 &&
          (job?.errors || []).length === 0 &&
          (job?.warnings || []).length === 0 &&
          (job?.logs || []).length === 0
        "
        description="暂无执行结果"
      />
    </Card>

    <Card title="事件流">
      <Table
        :columns="eventColumns"
        :data-source="events"
        :pagination="false"
        row-key="id"
        size="small"
        :scroll="{ x: 980 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'event_type'">
            <Tag :color="eventColor(record.event_type)">
              {{ record.event_type_label || record.event_type }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'worker_id'">
            <span class="font-mono">{{ empty(record.worker_id) }}</span>
          </template>
          <template v-else-if="column.key === 'payload'">
            <TypographyParagraph
              v-if="compactJson(record.payload)"
              class="!mb-0 whitespace-pre-wrap break-all font-mono text-xs leading-5"
              :ellipsis="{ rows: 4, expandable: true, symbol: '展开载荷' }"
            >
              {{ compactJson(record.payload) }}
            </TypographyParagraph>
            <span v-else>-</span>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>
