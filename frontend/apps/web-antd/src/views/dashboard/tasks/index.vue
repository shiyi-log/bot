<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardTaskCenterOverview,
  DashboardTaskCenterSection,
  DashboardTaskItem,
} from '#/api/admin';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  Space,
  Table,
  Tag,
  TypographyParagraph,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardTaskCenterApi, getDashboardTasksApi } from '#/api/admin';

const router = useRouter();
const loading = ref(false);
const keyword = ref('');
const overview = ref<DashboardTaskCenterOverview | null>(null);
const fallbackItems = ref<DashboardTaskItem[]>([]);

const columns: TableColumnsType<DashboardTaskItem> = [
  { title: '来源', dataIndex: 'task_label', key: 'task_label', width: 130 },
  { title: '对象', dataIndex: 'order_no', key: 'order_no', width: 200 },
  {
    title: '云平台',
    dataIndex: 'provider_label',
    key: 'provider_label',
    width: 110,
  },
  { title: '公网IP', dataIndex: 'public_ip', key: 'public_ip', width: 140 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 150 },
  {
    title: '执行状态',
    dataIndex: 'execution_status',
    key: 'execution_status',
    width: 150,
  },
  {
    title: '下次运行',
    dataIndex: 'next_run_at',
    key: 'next_run_at',
    width: 170,
  },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
  { title: '说明', dataIndex: 'note', key: 'note', width: 260 },
  { title: '操作', key: 'actions', width: 90, fixed: 'right' as const },
];

const sections = computed(() => overview.value?.sections || []);
const allItems = computed(() => {
  const sectionItems = sections.value.flatMap((section) =>
    (section.items || []).map((item) => ({
      ...item,
      task_label: item.task_label || section.title,
      task_type: item.task_type || section.key,
    })),
  );
  return sectionItems.length > 0 ? sectionItems : fallbackItems.value;
});
const filteredItems = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  if (!query) return allItems.value;
  return allItems.value.filter((item) =>
    [
      item.order_no,
      item.plan_name,
      item.provider_label,
      item.public_ip,
      item.status_label,
      item.execution_status_label,
      item.note,
      item.task_label,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query)),
  );
});

function asDashboardTaskItem(record: Record<string, any>) {
  return record as DashboardTaskItem;
}

function healthColor(health?: string) {
  if (health === 'error') return 'red';
  if (health === 'warning') return 'orange';
  return 'green';
}

function statusColor(status?: string) {
  if (
    ['active', 'auto_renew_success', 'completed', 'succeeded'].includes(
      status || '',
    )
  ) {
    return 'success';
  }
  if (
    [
      'auto_renew_pending',
      'deleting',
      'due_now',
      'expiring',
      'overdue',
      'paid',
      'provisioning',
      'queued',
      'renew_pending',
      'running',
      'scheduled_future',
      'suspended',
    ].includes(status || '')
  ) {
    return 'processing';
  }
  if (
    [
      'auto_renew_failed',
      'cancelled',
      'deleted',
      'expired',
      'failed',
      'partial',
    ].includes(status || '')
  ) {
    return 'error';
  }
  return 'default';
}

function formatTime(value?: null | string) {
  if (!value) return '-';
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}

function taskObjectLabel(item: DashboardTaskItem) {
  return (
    item.order_no ||
    (item.order_id ? `订单 ${item.order_id}` : String(item.id || '-'))
  );
}

async function loadData() {
  loading.value = true;
  try {
    try {
      overview.value = await getDashboardTaskCenterApi();
    } catch {
      overview.value = null;
      fallbackItems.value = await getDashboardTasksApi();
    }
  } finally {
    loading.value = false;
  }
}

function canOpenPath(path?: string) {
  return typeof path === 'string' && path.length > 0;
}

function openPath(path?: string) {
  if (path) {
    router.push(path).catch(() => {});
  }
}

function openTask(record: DashboardTaskItem) {
  openPath(record.detail_path || record.related_path);
}

function sectionKey(section: DashboardTaskCenterSection) {
  return section.key || section.title;
}

onMounted(loadData);
</script>

<template>
  <Page
    description="统一查看同步、云订单、生命周期、通知和自动续费任务状态"
    title="任务中心"
  >
    <div class="task-overview-grid">
      <Card class="task-total-card" :loading="loading">
        <div class="task-total-title">任务总量</div>
        <div class="task-total-value">
          {{ overview?.totals.tasks ?? filteredItems.length }}
        </div>
        <div class="task-total-meta">
          活动 {{ overview?.totals.active ?? 0 }} / 告警
          {{ overview?.totals.warning ?? 0 }} / 失败
          {{ overview?.totals.failed ?? 0 }}
        </div>
      </Card>
      <Card
        v-for="section in sections"
        :key="sectionKey(section)"
        class="task-section-card"
        :loading="loading"
        @click="openPath(section.path)"
      >
        <Space class="task-section-head" align="center">
          <Tag :color="healthColor(section.health)">
            {{
              section.health === 'error'
                ? '异常'
                : section.health === 'warning'
                  ? '关注'
                  : '正常'
            }}
          </Tag>
          <span>{{ section.title }}</span>
        </Space>
        <div class="task-section-count">
          {{ section.active }}/{{ section.total }}
        </div>
        <div class="task-section-meta">
          告警 {{ section.warning }} · 失败 {{ section.failed }}
        </div>
      </Card>
    </div>

    <Card class="mt-3">
      <template #title>
        <Space wrap>
          <span>任务明细</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索订单号 / 套餐 / IP / 状态"
            style="width: min(360px, 100%)"
            @search="loadData"
          />
          <Button size="small" :loading="loading" @click="loadData">
            刷新
          </Button>
          <span class="text-xs text-gray-500">
            生成时间：{{ formatTime(overview?.generated_at) }}
          </span>
        </Space>
      </template>
      <Table
        :columns="columns"
        :data-source="filteredItems"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 12 }"
        :scroll="{ x: 1420 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'order_no'">
            <span>{{ taskObjectLabel(asDashboardTaskItem(record)) }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="statusColor(asDashboardTaskItem(record).status)">
              {{
                asDashboardTaskItem(record).status_label ||
                asDashboardTaskItem(record).status ||
                '-'
              }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'execution_status'">
            <Tag
              :color="
                statusColor(
                  asDashboardTaskItem(record).execution_status ||
                    asDashboardTaskItem(record).status,
                )
              "
            >
              {{
                asDashboardTaskItem(record).execution_status_label ||
                asDashboardTaskItem(record).execution_status ||
                '-'
              }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'next_run_at'">
            {{ formatTime(asDashboardTaskItem(record).next_run_at) }}
          </template>
          <template v-else-if="column.key === 'updated_at'">
            {{ formatTime(asDashboardTaskItem(record).updated_at) }}
          </template>
          <template v-else-if="column.key === 'note'">
            <TypographyParagraph
              class="!mb-0 max-w-full break-all text-xs leading-5"
              :content="asDashboardTaskItem(record).note || '-'"
              :ellipsis="{
                rows: 2,
                tooltip: asDashboardTaskItem(record).note || '',
              }"
            />
          </template>
          <template v-else-if="column.key === 'actions'">
            <Button
              v-if="
                canOpenPath(
                  asDashboardTaskItem(record).detail_path ||
                    asDashboardTaskItem(record).related_path,
                )
              "
              type="link"
              size="small"
              @click="openTask(asDashboardTaskItem(record))"
            >
              详情
            </Button>
            <span v-else>-</span>
          </template>
        </template>
      </Table>
    </Card>
  </Page>
</template>

<style scoped>
.task-overview-grid {
  display: grid;
  grid-template-columns: 1.2fr repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.task-total-card,
.task-section-card {
  min-width: 0;
  border-radius: 6px;
}

.task-section-card {
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    transform 0.16s ease;
}

.task-section-card:hover {
  border-color: #1677ff;
  transform: translateY(-1px);
}

.task-total-title,
.task-section-meta {
  font-size: 12px;
  color: #6b7280;
}

.task-total-value,
.task-section-count {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 650;
  line-height: 30px;
  color: #111827;
}

.task-total-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #4b5563;
}

.task-section-head {
  min-width: 0;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .task-overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .task-overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
