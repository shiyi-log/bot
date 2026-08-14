<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudPlanItem,
  DashboardCloudPlanUpdatePayload,
  DashboardCloudPricingItem,
} from '#/api/admin';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createDashboardCloudPlanApi,
  deleteDashboardCloudPlanApi,
  getDashboardCloudPlansApi,
  getDashboardCloudPricingApi,
  updateDashboardCloudPlanApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const deletingId = ref<null | number>(null);
const keyword = ref('');
const activeTab = ref<'plans' | 'pricing'>('plans');
const plans = ref<DashboardCloudPlanItem[]>([]);
const pricing = ref<DashboardCloudPricingItem[]>([]);
const editOpen = ref(false);
const createMode = ref(false);
const editingPlan = ref<DashboardCloudPlanItem | null>(null);
const selectedRegionCode = ref<string | undefined>(undefined);
const selectedPricingPreset = ref<string | undefined>(undefined);
const editForm = ref<DashboardCloudPlanUpdatePayload>({
  provider: 'aws_lightsail',
  region_code: 'ap-southeast-1',
  region_name: '新加坡',
  provider_plan_id: '',
  plan_name: '',
  plan_description: '',
  cpu: '',
  memory: '',
  storage: '',
  bandwidth: '',
  currency: 'USDT',
  cost_price: 0,
  price: 0,
  sort_order: 0,
  is_active: true,
});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const providerOptions = [
  { label: 'AWS 光帆服务器', value: 'aws_lightsail' },
  { label: '阿里云轻量云', value: 'aliyun_simple' },
];

const planColumns: TableColumnsType<DashboardCloudPlanItem> = [
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 140 },
  { title: '厂商', dataIndex: 'provider', key: 'provider', width: 120 },
  { title: '配置ID', dataIndex: 'config_id', key: 'config_id', width: 220 },
  { title: '套餐名', dataIndex: 'plan_name', key: 'plan_name', width: 160 },
  {
    title: '展示套餐名',
    dataIndex: 'display_plan_name',
    key: 'display_plan_name',
    width: 180,
  },
  {
    title: '套餐文案',
    dataIndex: 'display_description',
    key: 'display_description',
    width: 320,
  },
  { title: 'CPU', dataIndex: 'cpu', key: 'cpu', width: 90 },
  { title: '内存', dataIndex: 'memory', key: 'memory', width: 90 },
  { title: '存储', dataIndex: 'storage', key: 'storage', width: 110 },
  { title: '带宽', dataIndex: 'bandwidth', key: 'bandwidth', width: 90 },
  { title: '进货价', dataIndex: 'cost_price', key: 'cost_price', width: 110 },
  { title: '出售价', dataIndex: 'price', key: 'price', width: 110 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 90 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 90 },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' as const },
];

const pricingColumns: TableColumnsType<DashboardCloudPricingItem> = [
  { title: '地区', dataIndex: 'region_label', key: 'region_label', width: 140 },
  { title: '厂商', dataIndex: 'provider', key: 'provider', width: 120 },
  { title: '套餐名', dataIndex: 'plan_name', key: 'plan_name', width: 140 },
  {
    title: '配置ID',
    dataIndex: 'config_id',
    key: 'config_id',
    width: 220,
  },
  {
    title: '规格编码',
    dataIndex: 'bundle_code',
    key: 'bundle_code',
    width: 220,
  },
  {
    title: '配置',
    dataIndex: 'plan_description',
    key: 'plan_description',
    width: 280,
  },
  { title: '进货价', dataIndex: 'cost_price', key: 'cost_price', width: 110 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 90 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 90 },
];

const currentColumns = computed(() =>
  activeTab.value === 'plans' ? planColumns : pricingColumns,
);
const currentItems = computed(() =>
  activeTab.value === 'plans' ? plans.value : pricing.value,
);

const regionOptions = computed(() => {
  const seen = new Set<string>();
  return pricing.value
    .filter((item) => item.provider === editForm.value.provider)
    .filter((item) => {
      const key = `${item.provider}::${item.region_code}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    })
    .map((item) => ({
      label: item.region_label || item.region_name || item.region_code,
      value: item.region_code,
    }));
});

const pricingPresetOptions = computed(() => {
  return pricing.value
    .filter((item) => item.provider === editForm.value.provider)
    .filter(
      (item) =>
        !selectedRegionCode.value ||
        item.region_code === selectedRegionCode.value,
    )
    .map((item) => ({
      label: `${item.plan_name} / ${item.cpu} ${item.memory} ${item.storage}`,
      value: `${item.provider}::${item.region_code}::${item.bundle_code}`,
    }));
});

function asDashboardCloudPlanItem(record: Record<string, any>) {
  return record as DashboardCloudPlanItem;
}

function generateConfigId() {
  return `cfg-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`;
}

function buildDefaultDisplayDescription(form: DashboardCloudPlanUpdatePayload) {
  const lines = [
    `适用地区：${form.region_name || form.region_code || '待填写'}`,
    `套餐配置：${form.cpu || '待填写'} / ${form.memory || '待填写'} / ${form.storage || '待填写'}`,
    `带宽流量：${form.bandwidth || '待填写'}`,
    '套餐说明：高速稳定，开箱即用，适合日常建站与轻量业务部署。',
  ];
  return lines.join('\n');
}

function fillDefaultDisplayDescription(force = false) {
  if (!force && editForm.value.display_description) {
    return;
  }
  editForm.value = {
    ...editForm.value,
    display_description: buildDefaultDisplayDescription(editForm.value),
  };
}

function resetEditForm() {
  selectedRegionCode.value = 'ap-southeast-1';
  selectedPricingPreset.value = undefined;
  editForm.value = {
    provider: 'aws_lightsail',
    region_code: 'ap-southeast-1',
    region_name: '新加坡',
    config_id: '',
    provider_plan_id: '',
    plan_name: '',
    plan_description: '',
    display_plan_name: '',
    display_cpu: '',
    display_memory: '',
    display_storage: '',
    display_bandwidth: '',
    display_description: '',
    cpu: '',
    memory: '',
    storage: '',
    bandwidth: '',
    currency: 'USDT',
    cost_price: 0,
    price: 0,
    sort_order: 0,
    is_active: true,
  };
  fillDefaultDisplayDescription(true);
}

async function loadData() {
  loading.value = true;
  try {
    const params = { keyword: keyword.value.trim() };
    const [planList, pricingList] = await Promise.all([
      getDashboardCloudPlansApi(params),
      getDashboardCloudPricingApi({}),
    ]);
    plans.value = planList;
    pricing.value = pricingList;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireCloudDangerPermission('新增套餐')) return;
  createMode.value = true;
  editingPlan.value = null;
  resetEditForm();
  editOpen.value = true;
}

function openEdit(record: DashboardCloudPlanItem) {
  if (!requireCloudDangerPermission('编辑套餐')) return;
  createMode.value = false;
  editingPlan.value = record;
  selectedRegionCode.value = record.region_code;
  const providerPlanId = (record as any).provider_plan_id || '';
  selectedPricingPreset.value = providerPlanId
    ? `${record.provider}::${record.region_code}::${providerPlanId}`
    : undefined;
  editForm.value = {
    provider: record.provider,
    region_code: record.region_code,
    region_name: record.region_name,
    config_id: (record as any).config_id || generateConfigId(),
    provider_plan_id: providerPlanId,
    plan_name: record.plan_name || '',
    plan_description:
      record.display_description || record.plan_description || '',
    display_plan_name: (record as any).display_plan_name || '',
    display_cpu: (record as any).display_cpu || '',
    display_memory: (record as any).display_memory || '',
    display_storage: (record as any).display_storage || '',
    display_bandwidth: (record as any).display_bandwidth || '',
    display_description: (record as any).display_description || '',
    cpu: record.cpu || '',
    memory: record.memory || '',
    storage: record.storage || '',
    bandwidth: record.bandwidth || '',
    currency: record.currency || 'USDT',
    cost_price: Number(record.cost_price || 0),
    price: Number(record.price || 0),
    sort_order: Number(record.sort_order || 0),
    is_active: !!record.is_active,
  };
  editOpen.value = true;
}

function applyRegion(regionCode?: unknown) {
  const normalizedRegionCode =
    typeof regionCode === 'string'
      ? regionCode
      : (regionCode === null || Array.isArray(regionCode)
        ? undefined
        : String(regionCode));
  selectedRegionCode.value = normalizedRegionCode;
  const selected = pricing.value.find(
    (item) =>
      item.provider === editForm.value.provider &&
      item.region_code === normalizedRegionCode,
  );
  editForm.value = {
    ...editForm.value,
    region_code: normalizedRegionCode || '',
    region_name: selected?.region_name || '',
  };
  selectedPricingPreset.value = undefined;
  fillDefaultDisplayDescription();
}

function applyPricingPreset(presetValue?: unknown) {
  const normalizedPresetValue =
    typeof presetValue === 'string'
      ? presetValue
      : (presetValue === null || Array.isArray(presetValue)
        ? undefined
        : String(presetValue));
  selectedPricingPreset.value = normalizedPresetValue;
  const selected = pricing.value.find(
    (item) =>
      `${item.provider}::${item.region_code}::${item.bundle_code}` ===
      normalizedPresetValue,
  );
  if (!selected) {
    return;
  }
  selectedRegionCode.value = selected.region_code;
  editForm.value = {
    ...editForm.value,
    provider: selected.provider,
    region_code: selected.region_code,
    region_name: selected.region_name,
    config_id: (selected as any).config_id || '',
    provider_plan_id: selected.bundle_code || '',
    plan_name: selected.plan_name,
    plan_description:
      editForm.value.display_description || selected.plan_description || '',
    display_plan_name: editForm.value.display_plan_name || selected.plan_name,
    cpu: selected.cpu || '',
    memory: selected.memory || '',
    storage: selected.storage || '',
    bandwidth: selected.bandwidth || '',
    currency: selected.currency || 'USDT',
    cost_price: Number(selected.cost_price || selected.price || 0),
  };
  fillDefaultDisplayDescription();
}

watch(
  () => editForm.value.provider,
  (provider) => {
    selectedPricingPreset.value = undefined;
    const firstRegion = pricing.value.find(
      (item) => item.provider === provider,
    )?.region_code;
    selectedRegionCode.value = firstRegion;
    if (createMode.value) {
      applyRegion(firstRegion);
    }
  },
);

async function saveEdit() {
  if (!requireCloudDangerPermission('保存套餐')) return;
  saving.value = true;
  try {
    const payload = {
      ...editForm.value,
      config_id: (editForm.value.config_id || generateConfigId()).trim(),
      plan_description: editForm.value.display_description || '',
    };
    if (createMode.value) {
      await createDashboardCloudPlanApi(payload);
      message.success('套餐已创建');
    } else if (editingPlan.value) {
      await updateDashboardCloudPlanApi(editingPlan.value.id, payload);
      message.success('套餐已更新');
    }
    editOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(
      error?.message || (createMode.value ? '套餐创建失败' : '套餐更新失败'),
    );
  } finally {
    saving.value = false;
  }
}

async function removePlan(planId: number) {
  if (!requireCloudDangerPermission('删除套餐')) return;
  deletingId.value = planId;
  try {
    await deleteDashboardCloudPlanApi(planId);
    message.success('套餐已删除');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '套餐删除失败');
  } finally {
    deletingId.value = null;
  }
}

function resetSearch() {
  keyword.value = '';
  loadData();
}

onMounted(loadData);
</script>

<template>
  <Page
    description="套餐与售价改为后台手动创建和维护；主规格与进货价请在配置同步页查看。"
    title="套餐列表"
  >
    <Card>
      <template #title>
        <Space>
          <span>套餐与售价</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索地区、厂商、套餐名"
            style="width: 360px"
            @search="loadData"
          />
          <Button
            size="small"
            :type="activeTab === 'plans' ? 'primary' : 'default'"
            @click="activeTab = 'plans'"
          >
            套餐列表
          </Button>
          <Button
            size="small"
            :type="activeTab === 'pricing' ? 'primary' : 'default'"
            @click="activeTab = 'pricing'"
          >
            价格列表
          </Button>
          <Button
            v-if="activeTab === 'plans'"
            size="small"
            type="primary"
            :disabled="!canRunCloudDanger"
            @click="openCreate"
          >
            新增套餐
          </Button>
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>
      <Table
        :columns="currentColumns"
        :data-source="currentItems"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 20 }"
        :scroll="{ x: 1700 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'provider'">
            <Tag color="blue">
              {{ record.provider_label || record.provider || '-' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'cost_price'">
            <Tag color="default">
              {{ record.cost_price || '0' }}
              {{ record.currency || 'USDT' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'price'">
            <Tag color="gold">
              {{ record.price }} {{ record.currency || 'USDT' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <Tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '启用' : '停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'display_description'">
            <span>{{
              record.display_description ||
              record.plan_description ||
              `${record.cpu} / ${record.memory} / ${record.storage} / ${record.bandwidth}`
            }}</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button
                type="link"
                size="small"
                :disabled="!canRunCloudDanger"
                @click="openEdit(asDashboardCloudPlanItem(record))"
              >
                编辑
              </Button>
              <Popconfirm
                title="确认删除该套餐？"
                @confirm="removePlan(record.id)"
              >
                <Button
                  type="link"
                  danger
                  size="small"
                  :disabled="!canRunCloudDanger"
                  :loading="deletingId === record.id"
                >
                  删除
                </Button>
              </Popconfirm>
            </Space>
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="editOpen"
      :title="createMode ? '新增套餐' : '编辑套餐'"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      @ok="saveEdit"
    >
      <Space direction="vertical" style="width: 100%">
        <Select
          v-model:value="editForm.provider"
          :options="providerOptions"
          placeholder="选择云厂商"
        />
        <Select
          v-model:value="selectedRegionCode"
          allow-clear
          show-search
          :filter-option="
            (input, option) =>
              String(option?.label || '')
                .toLowerCase()
                .includes(input.toLowerCase())
          "
          :options="regionOptions"
          placeholder="第二步：选择地区"
          @change="applyRegion"
        />
        <Select
          v-model:value="selectedPricingPreset"
          allow-clear
          show-search
          :disabled="!selectedRegionCode"
          :filter-option="
            (input, option) =>
              String(option?.label || '')
                .toLowerCase()
                .includes(input.toLowerCase())
          "
          :options="pricingPresetOptions"
          placeholder="第三步：选择配置，自动带入进货价（同步价）"
          @change="applyPricingPreset"
        />
        <Input
          v-model:value="editForm.region_code"
          :disabled="createMode"
          placeholder="地区代码，如 ap-southeast-1"
        />
        <Input
          v-model:value="editForm.region_name"
          :disabled="createMode"
          placeholder="地区名称，如 新加坡"
        />
        <Input
          :value="editForm.config_id || '选择同步配置后自动带入'"
          disabled
          placeholder="配置ID来自配置同步"
        />
        <Input v-model:value="editForm.plan_name" placeholder="套餐名" />
        <Input
          v-model:value="editForm.display_plan_name"
          placeholder="前台标题，如 新加坡轻量 2核4G"
        />
        <Input v-model:value="editForm.cpu" placeholder="CPU，如 2核" />
        <Input v-model:value="editForm.memory" placeholder="内存，如 2GB" />
        <Input
          v-model:value="editForm.storage"
          placeholder="存储，如 60GB SSD"
        />
        <Input
          v-model:value="editForm.bandwidth"
          placeholder="带宽，如 3TB / 30Mbps"
        />
        <Space style="justify-content: space-between; width: 100%">
          <div style="font-size: 13px; color: rgb(100 116 139)">
            套餐文案（可留空；需要时可恢复默认文案）
          </div>
          <Button size="small" @click="fillDefaultDisplayDescription(true)">
            恢复默认文案
          </Button>
        </Space>
        <Input.TextArea
          v-model:value="editForm.display_description"
          :auto-size="{ minRows: 8, maxRows: 14 }"
          placeholder="系统会自动带入默认套餐文案"
        />
        <Input v-model:value="editForm.currency" placeholder="币种" />
        <InputNumber
          v-model:value="editForm.cost_price"
          style="width: 100%"
          :min="0"
          :step="0.01"
          addon-before="进货价"
        />
        <InputNumber
          v-model:value="editForm.price"
          style="width: 100%"
          :min="0"
          :step="0.01"
          addon-before="出售价"
        />
        <InputNumber
          v-model:value="editForm.sort_order"
          style="width: 100%"
          :step="1"
          addon-before="排序"
        />
        <Space>
          <span>启用</span>
          <Switch v-model:checked="editForm.is_active" />
        </Space>
      </Space>
    </Modal>
  </Page>
</template>
