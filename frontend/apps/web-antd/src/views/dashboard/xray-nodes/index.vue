<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardXrayJobItem,
  DashboardXrayNodeItem,
  DashboardXraySubscriptionNodeItem,
  DashboardXraySubscriptionSettings,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Check, Copy } from '@vben/icons';

import {
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  message,
  Row,
  Segmented,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'ant-design-vue';

import {
  createDashboardXrayNodeApi,
  getDashboardXrayNodesApi,
  getDashboardXraySubscriptionSettingsApi,
  revealDashboardXraySubscriptionLinkApi,
  sweepDashboardXraySubscriptionApi,
  updateDashboardXraySubscriptionSettingsApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const creating = ref(false);
const sweeping = ref(false);
const subscriptionLoading = ref(false);
const subscriptionSaving = ref(false);
const subscriptionCopying = ref(false);
type SubscriptionClient = 'clash' | 'mihomo' | 'shadowrocket' | 'v2ray';
const subscriptionClient = ref<SubscriptionClient>('shadowrocket');
const subscriptionClientOptions: Array<{
  label: string;
  value: SubscriptionClient;
}> = [
  { label: 'Shadowrocket', value: 'shadowrocket' },
  { label: 'Clash', value: 'clash' },
  { label: 'Mihomo', value: 'mihomo' },
  { label: 'V2Ray', value: 'v2ray' },
];
const subscriptionClientLabel = computed(
  () =>
    subscriptionClientOptions.find(
      (option) => option.value === subscriptionClient.value,
    )?.label || 'Shadowrocket',
);
const nodes = ref<DashboardXrayNodeItem[]>([]);
const subscriptionNodes = ref<DashboardXraySubscriptionNodeItem[]>([]);
const jobs = ref<DashboardXrayJobItem[]>([]);
const errors = ref<Array<{ error: string; region: string }>>([]);
const summary = reactive({
  live_count: 0,
  local_count: 0,
  running_count: 0,
  subscription_active_count: 0,
  subscription_inactive_count: 0,
  total: 0,
});
const subscriptionSettings = reactive<DashboardXraySubscriptionSettings>({
  config_error: '',
  configured: false,
  report_domain: '',
  report_host: '',
  source: '',
  subscription_link_available: false,
  token_available: false,
});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const createForm = reactive({
  confirm_text: '',
  order_id: undefined as number | undefined,
});

const sweepForm = reactive({
  confirm_text: '',
  failure_threshold: 3,
  timeout: 5,
});

const subscriptionForm = reactive({
  report_domain: '',
});

const nodeColumns = computed<TableColumnsType<DashboardXrayNodeItem>>(() => [
  { title: '节点名', dataIndex: 'name', key: 'name', width: 260 },
  { title: '区域', dataIndex: 'region', key: 'region', width: 150 },
  { title: '状态', dataIndex: 'state', key: 'state', width: 120 },
  { title: '套餐', dataIndex: 'bundle', key: 'bundle', width: 120 },
  { title: '镜像', dataIndex: 'blueprint', key: 'blueprint', width: 140 },
  {
    title: '公网 IP',
    dataIndex: 'public_ip_masked',
    key: 'public_ip_masked',
    width: 150,
  },
  { title: '协议', key: 'protocols', width: 280 },
  { title: '验证', key: 'verification', width: 220 },
]);

const jobColumns: TableColumnsType<DashboardXrayJobItem> = [
  { title: '任务 ID', dataIndex: 'id', key: 'id', width: 180 },
  { title: 'Shop 订单', dataIndex: 'order_no', key: 'order_no', width: 210 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  {
    title: '计划安装时间',
    dataIndex: 'scheduled_at',
    key: 'scheduled_at',
    width: 220,
  },
  { title: '尝试次数', key: 'attempts', width: 120 },
  {
    title: '完成时间',
    dataIndex: 'finished_at',
    key: 'finished_at',
    width: 220,
  },
  {
    title: '输出摘要',
    dataIndex: 'output_tail',
    key: 'output_tail',
    width: 360,
  },
];

const subscriptionNodeColumns: TableColumnsType<DashboardXraySubscriptionNodeItem> =
  [
    { title: '节点名', dataIndex: 'node_name', key: 'node_name', width: 240 },
    { title: '区域', dataIndex: 'region', key: 'region', width: 150 },
    {
      title: '公网 IP',
      dataIndex: 'public_ip_masked',
      key: 'public_ip_masked',
      width: 150,
    },
    { title: '订阅状态', dataIndex: 'status', key: 'status', width: 120 },
    { title: '协议', key: 'protocols', width: 280 },
    {
      title: '连续失败',
      dataIndex: 'failure_count',
      key: 'failure_count',
      width: 110,
    },
    {
      title: '最近检查',
      dataIndex: 'last_checked_at',
      key: 'last_checked_at',
      width: 210,
    },
    {
      title: '下次检查',
      dataIndex: 'next_check_at',
      key: 'next_check_at',
      width: 210,
    },
    {
      title: '最近错误',
      dataIndex: 'last_error',
      key: 'last_error',
      width: 260,
    },
  ];

function stateColor(state?: string) {
  if (state === 'running') return 'green';
  if (state === 'missing') return 'orange';
  if (state === 'stopped') return 'default';
  return 'blue';
}

function jobColor(status?: string) {
  if (status === 'succeeded') return 'green';
  if (status === 'failed') return 'red';
  if (status === 'running') return 'blue';
  return 'default';
}

async function loadData() {
  loading.value = true;
  try {
    const response = await getDashboardXrayNodesApi();
    nodes.value = response.items || [];
    subscriptionNodes.value = response.subscription_nodes || [];
    jobs.value = response.jobs || [];
    errors.value = response.errors || [];
    Object.assign(summary, response.summary || {});
  } catch (error: any) {
    message.error(error?.message || '加载 Xray 节点失败');
  } finally {
    loading.value = false;
  }
}

function applySubscriptionSettings(data: DashboardXraySubscriptionSettings) {
  Object.assign(subscriptionSettings, data);
  subscriptionForm.report_domain = data.report_domain || '';
}

async function loadSubscriptionSettings() {
  subscriptionLoading.value = true;
  try {
    const response = await getDashboardXraySubscriptionSettingsApi();
    applySubscriptionSettings(response);
  } catch (error: any) {
    message.error(error?.message || '加载订阅设置失败');
  } finally {
    subscriptionLoading.value = false;
  }
}

async function saveSubscriptionSettings() {
  if (!requireCloudDangerPermission('保存订阅设置')) return;
  subscriptionSaving.value = true;
  try {
    const response = await updateDashboardXraySubscriptionSettingsApi({
      report_domain: subscriptionForm.report_domain.trim(),
    });
    applySubscriptionSettings(response);
    message.success('Shop 公网地址已保存');
  } catch (error: any) {
    message.error(error?.message || '保存 Shop 公网地址失败');
  } finally {
    subscriptionSaving.value = false;
  }
}

async function copySubscriptionLink() {
  if (!requireCloudDangerPermission('复制订阅链接')) return;
  subscriptionCopying.value = true;
  try {
    const response = await revealDashboardXraySubscriptionLinkApi();
    const urlField = {
      clash: 'clash_subscription_url',
      mihomo: 'mihomo_subscription_url',
      shadowrocket: 'subscription_url',
      v2ray: 'v2ray_subscription_url',
    } as const;
    const url = String(
      response[urlField[subscriptionClient.value]] || '',
    ).trim();
    if (!url) {
      message.warning(`${subscriptionClientLabel.value} 订阅链接不可用`);
      return;
    }
    await navigator.clipboard.writeText(url);
    message.success(`${subscriptionClientLabel.value} 订阅链接已复制`);
  } catch (error: any) {
    message.error(error?.message || '复制订阅链接失败');
  } finally {
    subscriptionCopying.value = false;
  }
}

async function submitCreate() {
  if (!requireCloudDangerPermission('补排 Xray 安装')) return;
  const orderId = createForm.order_id;
  if (!orderId) {
    message.error('请输入 Shop 云服务器订单 ID');
    return;
  }
  if (createForm.confirm_text !== '确认安排Xray安装') {
    message.error('请输入确认文本');
    return;
  }
  creating.value = true;
  try {
    await createDashboardXrayNodeApi({
      confirm_text: createForm.confirm_text,
      order_id: orderId,
    });
    message.success('Xray 延迟安装任务已安排');
    createForm.confirm_text = '';
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '安排 Xray 安装任务失败');
  } finally {
    creating.value = false;
  }
}

async function submitSweep() {
  if (!requireCloudDangerPermission('清理订阅节点')) return;
  if (sweepForm.confirm_text !== '确认清理订阅') {
    message.error('订阅清理需要输入确认文本');
    return;
  }
  sweeping.value = true;
  try {
    const response = await sweepDashboardXraySubscriptionApi({ ...sweepForm });
    const disabled = response.result?.disabled ?? 0;
    message.success(`清理完成，禁用 ${disabled} 个节点`);
    sweepForm.confirm_text = '';
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '订阅清理失败');
  } finally {
    sweeping.value = false;
  }
}

onMounted(() => {
  void Promise.all([loadData(), loadSubscriptionSettings()]);
});
</script>

<template>
  <Page
    description="Shop 开通完成 20 分钟后安装 Xray，并管理订阅和清理"
    title="Xray 节点"
  >
    <Row :gutter="[12, 12]">
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic title="在线节点" :value="summary.running_count" />
        </Card>
      </Col>
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic title="云端节点" :value="summary.live_count" />
        </Card>
      </Col>
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic title="本地记录" :value="summary.local_count" />
        </Card>
      </Col>
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic title="合计" :value="summary.total" />
        </Card>
      </Col>
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic
            title="订阅中"
            :value="summary.subscription_active_count"
          />
        </Card>
      </Col>
      <Col :lg="4" :md="8" :xs="12">
        <Card size="small">
          <Statistic
            title="已停用"
            :value="summary.subscription_inactive_count"
          />
        </Card>
      </Col>
    </Row>

    <Card class="mt-3" title="订阅设置">
      <Form layout="vertical">
        <Row :gutter="12" align="bottom">
          <Col :lg="14" :xs="24">
            <Form.Item label="Shop 公网地址">
              <Input
                v-model:value="subscriptionForm.report_domain"
                :disabled="subscriptionLoading"
                placeholder="https://sub.example.com"
                @press-enter="saveSubscriptionSettings"
              />
            </Form.Item>
          </Col>
          <Col :lg="10" :xs="24">
            <Form.Item label="状态">
              <Space wrap>
                <Tag
                  :color="subscriptionSettings.configured ? 'green' : 'orange'"
                >
                  {{
                    subscriptionSettings.configured
                      ? '公网地址已配置'
                      : '公网地址未配置'
                  }}
                </Tag>
                <Tag
                  :color="
                    subscriptionSettings.token_available ? 'green' : 'orange'
                  "
                >
                  {{
                    subscriptionSettings.token_available
                      ? '凭证可用'
                      : '凭证不可用'
                  }}
                </Tag>
              </Space>
            </Form.Item>
          </Col>
        </Row>
        <Typography.Text
          v-if="subscriptionSettings.config_error"
          class="mb-3 block"
          type="danger"
        >
          {{ subscriptionSettings.config_error }}
        </Typography.Text>
        <Space direction="vertical" size="small">
          <Segmented
            v-model:value="subscriptionClient"
            :options="subscriptionClientOptions"
            size="small"
          />
          <Space wrap>
            <Button
              type="primary"
              :disabled="!canRunCloudDanger || subscriptionLoading"
              :loading="subscriptionSaving"
              @click="saveSubscriptionSettings"
            >
              <template #icon><Check class="size-4" /></template>
              保存
            </Button>
            <Button
              :disabled="
                !canRunCloudDanger ||
                !subscriptionSettings.subscription_link_available
              "
              :loading="subscriptionCopying"
              @click="copySubscriptionLink"
            >
              <template #icon><Copy class="size-4" /></template>
              复制 {{ subscriptionClientLabel }} 链接
            </Button>
          </Space>
        </Space>
      </Form>
    </Card>

    <Card class="mt-3" title="订阅节点">
      <Table
        :columns="subscriptionNodeColumns"
        :data-source="subscriptionNodes"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        row-key="id"
        size="small"
        :scroll="{ x: 1730 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <Tag :color="record.status === 'active' ? 'green' : 'default'">
              {{ record.status === 'active' ? '订阅中' : '已停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'protocols'">
            <Space wrap>
              <Tag v-for="item in record.protocols || []" :key="item">
                {{ item }}
              </Tag>
            </Space>
          </template>
          <template
            v-else-if="
              column.key === 'last_checked_at' || column.key === 'next_check_at'
            "
          >
            {{
              (column.key === 'last_checked_at'
                ? record.last_checked_at
                : record.next_check_at) || '-'
            }}
          </template>
          <template v-else-if="column.key === 'last_error'">
            <Typography.Text type="secondary">
              {{ record.last_error || '-' }}
            </Typography.Text>
          </template>
        </template>
      </Table>
    </Card>

    <Card class="mt-3" title="节点库存">
      <template #extra>
        <Button :loading="loading" size="small" @click="loadData">刷新</Button>
      </template>
      <Space v-if="errors.length > 0" class="mb-3" wrap>
        <Tag v-for="item in errors" :key="item.region" color="orange">
          {{ item.region }} {{ item.error }}
        </Tag>
      </Space>
      <Table
        :columns="nodeColumns"
        :data-source="nodes"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        row-key="name"
        size="small"
        :scroll="{ x: 1500 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'state'">
            <Tag :color="stateColor(record.state)">
              {{ record.state || '-' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'protocols'">
            <Space wrap>
              <Tag
                v-for="item in record.local_metadata?.protocols || []"
                :key="item"
              >
                {{ item }}
              </Tag>
              <Typography.Text
                v-if="!record.local_metadata?.protocols?.length"
                type="secondary"
              >
                -
              </Typography.Text>
            </Space>
          </template>
          <template v-else-if="column.key === 'verification'">
            <Space wrap>
              <Tag
                :color="record.local_metadata?.health_ok ? 'green' : 'default'"
              >
                健康页
              </Tag>
              <Tag
                :color="record.local_metadata?.socks5_ok ? 'green' : 'default'"
              >
                SOCKS5
              </Tag>
              <Tag
                :color="
                  record.local_metadata?.has_subscription_publish
                    ? 'green'
                    : 'default'
                "
              >
                订阅
              </Tag>
              <Tag
                v-if="record.local_metadata?.static_ip_fallback_reason"
                color="orange"
              >
                临时 IP
              </Tag>
            </Space>
          </template>
        </template>
      </Table>
    </Card>

    <Row class="mt-3" :gutter="[12, 12]">
      <Col :lg="14" :xs="24">
        <Card title="补排延迟安装">
          <Form layout="vertical">
            <Row :gutter="12">
              <Col :md="12" :xs="24">
                <Form.Item label="Shop 云服务器订单 ID">
                  <InputNumber
                    v-model:value="createForm.order_id"
                    :min="1"
                    :precision="0"
                    class="w-full"
                  />
                </Form.Item>
              </Col>
              <Col :md="12" :xs="24">
                <Form.Item label="确认文本">
                  <Input
                    v-model:value="createForm.confirm_text"
                    placeholder="输入：确认安排Xray安装"
                  />
                </Form.Item>
              </Col>
            </Row>
            <Button
              type="primary"
              :disabled="!canRunCloudDanger"
              :loading="creating"
              @click="submitCreate"
            >
              安排安装任务
            </Button>
          </Form>
        </Card>
      </Col>
      <Col :lg="10" :xs="24">
        <Card title="订阅清理">
          <Form layout="vertical">
            <Row :gutter="12">
              <Col :span="12">
                <Form.Item label="失败阈值">
                  <InputNumber
                    v-model:value="sweepForm.failure_threshold"
                    :min="1"
                    :max="10"
                    class="w-full"
                  />
                </Form.Item>
              </Col>
              <Col :span="12">
                <Form.Item label="超时秒数">
                  <InputNumber
                    v-model:value="sweepForm.timeout"
                    :min="1"
                    :max="30"
                    class="w-full"
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="确认文本">
              <Input
                v-model:value="sweepForm.confirm_text"
                placeholder="输入：确认清理订阅"
              />
            </Form.Item>
            <Button
              :disabled="!canRunCloudDanger"
              :loading="sweeping"
              @click="submitSweep"
            >
              执行清理
            </Button>
          </Form>
        </Card>
      </Col>
    </Row>

    <Card class="mt-3" title="任务记录">
      <Table
        :columns="jobColumns"
        :data-source="jobs"
        :pagination="{ pageSize: 10 }"
        row-key="id"
        size="small"
        :scroll="{ x: 1450 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <Tag :color="jobColor(record.status)">{{ record.status }}</Tag>
          </template>
          <template v-else-if="column.key === 'attempts'">
            {{ record.attempt_count || 0 }} / {{ record.max_attempts || 0 }}
          </template>
          <template v-else-if="column.key === 'output_tail'">
            <Typography.Paragraph
              class="xray-output"
              :ellipsis="{ rows: 3, expandable: true, symbol: '展开' }"
            >
              {{ record.output_tail || '-' }}
            </Typography.Paragraph>
          </template>
        </template>
      </Table>
    </Card>

    <Card class="mt-3" title="安全边界">
      <Descriptions :column="1" size="small">
        <Descriptions.Item label="敏感信息">
          节点列表只展示脱敏
          IP、协议名和任务摘要；完整订阅链接仅在超级管理员点击复制时按需读取。
        </Descriptions.Item>
        <Descriptions.Item label="真实成本">
          创建真实 AWS 资源必须勾选真实执行，并输入确认文本。
        </Descriptions.Item>
        <Descriptions.Item label="删除操作">
          Xray 节点删除已禁用，实例与绑定静态 IP 仅保留，不提供后台删除入口。
        </Descriptions.Item>
      </Descriptions>
    </Card>
  </Page>
</template>

<style scoped>
.xray-output {
  max-width: 340px;
  margin-bottom: 0;
  white-space: pre-wrap;
}
</style>
