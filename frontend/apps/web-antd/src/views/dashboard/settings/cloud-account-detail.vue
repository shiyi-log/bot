<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudAccountDetail,
  DashboardCloudAccountLogItem,
  DashboardCloudAccountServerRegionStatistics,
  DashboardCloudAccountStatistics,
} from '#/api/admin';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, RotateCw } from '@vben/icons';

import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  message,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getDashboardCloudAccountDetailApi,
  getDashboardCloudAccountStatisticsApi,
} from '#/api/admin';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const detail = ref<DashboardCloudAccountDetail | null>(null);
const statistics = ref<DashboardCloudAccountStatistics | null>(null);

const accountId = computed(() => Number(route.params.id || 0));
const billingAmounts = computed(() => statistics.value?.billing.amounts || []);

const regionColumns: TableColumnsType<DashboardCloudAccountServerRegionStatistics> =
  [
    {
      title: '地区',
      dataIndex: 'region_label',
      key: 'region_label',
      width: 180,
    },
    {
      title: '地区代码',
      dataIndex: 'region_code',
      key: 'region_code',
      width: 160,
    },
    {
      title: '当前服务器',
      dataIndex: 'total_count',
      key: 'total_count',
      width: 130,
    },
    {
      title: '运行中',
      dataIndex: 'running_count',
      key: 'running_count',
      width: 110,
    },
    {
      title: '停机/到期',
      dataIndex: 'stopped_count',
      key: 'stopped_count',
      width: 120,
    },
    {
      title: '其他状态',
      dataIndex: 'other_count',
      key: 'other_count',
      width: 110,
    },
  ];

const logColumns: TableColumnsType<DashboardCloudAccountLogItem> = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '来源', dataIndex: 'source_label', key: 'source_label', width: 120 },
  { title: '动作', dataIndex: 'action', key: 'action', width: 180 },
  { title: '目标', dataIndex: 'target', key: 'target', width: 220 },
  { title: '结果', dataIndex: 'is_success', key: 'is_success', width: 100 },
  { title: '错误', dataIndex: 'error_message', key: 'error_message' },
];

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function accountStatusColor(status?: null | string) {
  if (status === 'ok') return 'success';
  if (status === 'error') return 'error';
  return 'default';
}

function billingStatusColor(status?: string) {
  if (status === 'available') return 'success';
  if (status === 'unavailable') return 'warning';
  return 'default';
}

function regionRowKey(record: DashboardCloudAccountServerRegionStatistics) {
  return `${record.region_code || '-'}:${record.region_name || '-'}`;
}

async function loadData() {
  if (!accountId.value) {
    detail.value = null;
    statistics.value = null;
    return;
  }
  loading.value = true;
  const [detailResult, statisticsResult] = await Promise.allSettled([
    getDashboardCloudAccountDetailApi(accountId.value),
    getDashboardCloudAccountStatisticsApi(accountId.value),
  ]);
  if (detailResult.status === 'fulfilled') {
    detail.value = detailResult.value;
  } else {
    detail.value = null;
    message.error('加载云账号详情失败');
  }
  if (statisticsResult.status === 'fulfilled') {
    statistics.value = statisticsResult.value;
  } else {
    statistics.value = null;
    message.error('加载云账号账单和服务器统计失败');
  }
  loading.value = false;
}

function goBack() {
  router.push('/admin/cloud-accounts').catch(() => {});
}

onMounted(loadData);
</script>

<template>
  <Page description="云厂商当月账单与 Shop 服务器统计" title="云账号详情">
    <div class="account-detail-toolbar">
      <Button size="small" @click="goBack">
        <template #icon><ArrowLeft class="size-4" /></template>
        返回
      </Button>
      <span class="account-detail-title">
        {{ detail?.name || `云账号 #${accountId}` }}
      </span>
      <Tag v-if="detail" color="blue">
        {{ detail.provider_label || detail.provider }}
      </Tag>
      <Tag v-if="detail" :color="accountStatusColor(detail.status)">
        {{ detail.status_label || detail.status || '待检查' }}
      </Tag>
      <Button size="small" :loading="loading" @click="loadData">
        <template #icon><RotateCw class="size-4" /></template>
        刷新
      </Button>
    </div>

    <template v-if="detail">
      <Row :gutter="[12, 12]">
        <Col :xs="24" :lg="8">
          <Card class="summary-card" size="small" title="账号当前账单">
            <template #extra>
              <Tag
                v-if="statistics?.billing"
                :color="billingStatusColor(statistics.billing.status)"
              >
                {{ statistics.billing.status_label }}
              </Tag>
            </template>
            <template
              v-if="
                statistics?.billing.status === 'available' &&
                billingAmounts.length > 0
              "
            >
              <Space :size="24" wrap>
                <Statistic
                  v-for="item in billingAmounts"
                  :key="item.currency"
                  :precision="2"
                  :suffix="item.currency"
                  :title="`${statistics.billing.period} 累计`"
                  :value="Number(item.amount || 0)"
                />
              </Space>
              <div class="summary-meta">
                {{ statistics.billing.source_label || '-' }} ·
                {{ formatTime(statistics.billing.fetched_at) }}
              </div>
            </template>
            <Alert
              v-else
              :message="statistics?.billing.error || '账单暂不可用'"
              show-icon
              type="warning"
            />
          </Card>
        </Col>
        <Col :xs="12" :sm="8" :lg="3">
          <Card class="summary-card" size="small">
            <Statistic
              title="当前服务器"
              :value="statistics?.servers.total_count || 0"
            />
          </Card>
        </Col>
        <Col :xs="12" :sm="8" :lg="3">
          <Card class="summary-card" size="small">
            <Statistic
              title="运行中"
              :value="statistics?.servers.running_count || 0"
            />
          </Card>
        </Col>
        <Col :xs="12" :sm="8" :lg="3">
          <Card class="summary-card" size="small">
            <Statistic
              title="停机/到期"
              :value="statistics?.servers.stopped_count || 0"
            />
          </Card>
        </Col>
        <Col :xs="12" :sm="8" :lg="3">
          <Card class="summary-card" size="small">
            <Statistic
              title="其他状态"
              :value="statistics?.servers.other_count || 0"
            />
          </Card>
        </Col>
        <Col :xs="12" :sm="8" :lg="4">
          <Card class="summary-card" size="small">
            <Statistic
              title="历史记录"
              :value="statistics?.servers.historical_count || 0"
            />
          </Card>
        </Col>
      </Row>

      <Card class="detail-section" size="small" title="地区服务器数量">
        <Table
          :columns="regionColumns"
          :data-source="statistics?.servers.regions || []"
          :loading="loading"
          :pagination="false"
          :row-key="regionRowKey"
          :scroll="{ x: 810 }"
          size="small"
        />
        <Empty
          v-if="!loading && !statistics?.servers.regions.length"
          description="该账号暂无当前服务器"
        />
      </Card>

      <Card class="detail-section" size="small" title="账号信息">
        <Descriptions bordered :column="2" size="small">
          <Descriptions.Item label="内部 ID">{{ detail.id }}</Descriptions.Item>
          <Descriptions.Item label="云厂商">
            {{ detail.provider_label || detail.provider }}
          </Descriptions.Item>
          <Descriptions.Item label="账号 ID">
            {{ detail.external_account_id || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="默认地区">
            {{ detail.effective_region || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="Access Key">
            {{ detail.access_key_preview || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="Secret Key">
            {{ detail.secret_key_preview || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="当前服务器 / 全部记录">
            {{ statistics?.servers.total_count || 0 }} /
            {{ statistics?.servers.registered_count || 0 }}
          </Descriptions.Item>
          <Descriptions.Item label="关联订单">
            {{ detail.cloud_order_count }}
          </Descriptions.Item>
          <Descriptions.Item label="启用状态">
            {{ detail.is_active ? '启用' : '停用' }}
          </Descriptions.Item>
          <Descriptions.Item label="创建服务器">
            {{ detail.provision_enabled !== false ? '允许' : '禁止' }}
          </Descriptions.Item>
          <Descriptions.Item label="最近巡检">
            {{ formatTime(detail.last_checked_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {{ formatTime(detail.updated_at) }}
          </Descriptions.Item>
          <Descriptions.Item label="状态说明" :span="2">
            {{ detail.status_note || '-' }}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card class="detail-section" size="small" title="最近执行日志">
        <Table
          :columns="logColumns"
          :data-source="detail.recent_logs || []"
          :loading="loading"
          row-key="id"
          :pagination="{ pageSize: 10, showSizeChanger: false }"
          :scroll="{ x: 980 }"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'created_at'">
              {{ formatTime(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'is_success'">
              <Tag :color="record.is_success ? 'success' : 'error'">
                {{ record.is_success ? '成功' : '失败' }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'error_message'">
              <span class="log-error">{{ record.error_message || '-' }}</span>
            </template>
          </template>
        </Table>
      </Card>
    </template>

    <Empty v-else-if="!loading" description="云账号不存在或无权查看" />
  </Page>
</template>

<style scoped>
.account-detail-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.account-detail-title {
  font-size: 16px;
  font-weight: 600;
}

.summary-card {
  height: 100%;
}

.summary-meta {
  margin-top: 10px;
  font-size: 12px;
  color: var(--ant-color-text-secondary);
}

.detail-section {
  margin-top: 12px;
}

.log-error {
  display: block;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--ant-color-error);
  white-space: nowrap;
}
</style>
