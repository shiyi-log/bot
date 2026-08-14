<script lang="ts" setup>
import type { CollapseProps, TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudPlanSyncResult,
  DashboardCloudPricingItem,
} from '#/api/admin';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Collapse,
  Empty,
  Input,
  message,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  getDashboardCloudPricingApi,
  syncDashboardCloudPlansApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

interface RegionGroupItem {
  currency: string;
  pricing: DashboardCloudPricingItem[];
  provider: string;
  providerLabel: string;
  regionCode: string;
  regionName: string;
}

interface ProviderGroupItem {
  key: string;
  label: string;
  regions: RegionGroupItem[];
}

const loading = ref(false);
const syncing = ref(false);
const syncSummary = ref<DashboardCloudPlanSyncResult | null>(null);
const keyword = ref('');
const pricing = ref<DashboardCloudPricingItem[]>([]);
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const providerNameMap: Record<string, string> = {
  aliyun_simple: '阿里云',
  aws_lightsail: 'AWS',
};

const providerPriority: Record<string, number> = {
  aws_lightsail: 0,
  aliyun_simple: 1,
};

const providerRegionDisplayMap: Record<string, Record<string, string>> = {
  aws_lightsail: {
    'ap-southeast-1': '新加坡',
  },
  aliyun_simple: {
    'cn-hongkong': '香港',
  },
};

const pricingColumns: TableColumnsType<DashboardCloudPricingItem> = [
  { title: '在售规格', dataIndex: 'plan_name', key: 'plan_name', width: 140 },
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
    width: 180,
  },
  {
    title: '配置说明',
    dataIndex: 'plan_description',
    key: 'plan_description',
    width: 320,
  },
  { title: 'CPU', dataIndex: 'cpu', key: 'cpu', width: 90 },
  { title: '内存', dataIndex: 'memory', key: 'memory', width: 90 },
  { title: '存储', dataIndex: 'storage', key: 'storage', width: 120 },
  { title: '带宽', dataIndex: 'bandwidth', key: 'bandwidth', width: 100 },
  { title: '进货价', dataIndex: 'cost_price', key: 'cost_price', width: 120 },
  { title: '币种', dataIndex: 'currency', key: 'currency', width: 100 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 90 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 90 },
];

function normalizeProviderLabel(provider: string, label?: string) {
  return label || providerNameMap[provider] || provider;
}

function normalizeRegionLabel(item: DashboardCloudPricingItem) {
  const code = (item.region_code || '').trim();
  const mapped = providerRegionDisplayMap[item.provider]?.[code];
  if (mapped) {
    return mapped;
  }
  return item.region_label || item.region_name || code;
}

function isApacRegion(regionCode: string, regionName: string) {
  const text = `${regionCode} ${regionName}`.toLowerCase();
  return (
    text.includes('ap-') ||
    text.includes('asia') ||
    text.includes('pacific') ||
    /新加坡|香港|东京|首尔|悉尼|雅加达|曼谷|孟买|亚太/.test(regionName)
  );
}

function getRegionSortScore(region: RegionGroupItem) {
  const regionName = region.regionName || '';
  const regionCode = (region.regionCode || '').toLowerCase();
  if (regionName.includes('新加坡') || regionCode === 'ap-southeast-1') {
    return 0;
  }
  return isApacRegion(region.regionCode, region.regionName) ? 1 : 2;
}

const groupedProviders = computed<ProviderGroupItem[]>(() => {
  const providerMap = new Map<string, ProviderGroupItem>();
  const regionMap = new Map<string, RegionGroupItem>();

  for (const item of pricing.value) {
    const providerKey = item.provider;
    const regionKey = `${item.provider}__${item.region_code}`;
    if (!providerMap.has(providerKey)) {
      providerMap.set(providerKey, {
        key: providerKey,
        label: normalizeProviderLabel(item.provider, item.provider_label),
        regions: [],
      });
    }
    if (!regionMap.has(regionKey)) {
      const region = {
        provider: item.provider,
        providerLabel: normalizeProviderLabel(
          item.provider,
          item.provider_label,
        ),
        regionCode: item.region_code,
        regionName: normalizeRegionLabel(item),
        currency: item.currency || 'USDT',
        pricing: [],
      };
      regionMap.set(regionKey, region);
      providerMap.get(providerKey)?.regions.push(region);
    }
    const current = regionMap.get(regionKey);
    if (current) {
      current.currency = item.currency || current.currency || 'USDT';
      current.pricing.push(item);
    }
  }

  return [...providerMap.values()]
    .map((provider) => ({
      ...provider,
      regions: provider.regions
        .filter((region) => region.pricing.length > 0)
        .toSorted((left, right) => {
          const scoreDiff =
            getRegionSortScore(left) - getRegionSortScore(right);
          if (scoreDiff !== 0) {
            return scoreDiff;
          }
          return `${left.regionName}${left.regionCode}`.localeCompare(
            `${right.regionName}${right.regionCode}`,
            'zh-CN',
          );
        }),
    }))
    .filter((provider) => provider.regions.length > 0)
    .toSorted((left, right) => {
      const priorityDiff =
        (providerPriority[left.key] ?? 99) -
        (providerPriority[right.key] ?? 99);
      if (priorityDiff !== 0) {
        return priorityDiff;
      }
      return left.label.localeCompare(right.label, 'zh-CN');
    });
});

const providerActiveKeys = ref<string[]>(['aws_lightsail']);
const regionActiveKeys = ref<Record<string, string[]>>({});

function updateProviderActiveKeys(keys: CollapseProps['activeKey']) {
  providerActiveKeys.value = Array.isArray(keys)
    ? keys.map(String)
    : (keys
      ? [String(keys)]
      : []);
}

function getRegionActiveKeys(provider: ProviderGroupItem) {
  return regionActiveKeys.value[provider.key] || [];
}

function updateRegionActiveKeys(
  providerKey: string,
  keys: CollapseProps['activeKey'],
) {
  regionActiveKeys.value = {
    ...regionActiveKeys.value,
    [providerKey]: Array.isArray(keys)
      ? keys.map(String)
      : (keys
        ? [String(keys)]
        : []),
  };
}

function formatMoney(value: number | string | undefined, currency = 'USDT') {
  const numberValue = Number(value || 0);
  return `${numberValue.toFixed(2)} ${currency}`;
}

async function loadData() {
  loading.value = true;
  try {
    const params = { keyword: keyword.value.trim() };
    pricing.value = await getDashboardCloudPricingApi(params);
  } finally {
    loading.value = false;
  }
}

async function syncPricing() {
  if (!requireCloudDangerPermission('同步主规格与进货价')) return;
  syncing.value = true;
  try {
    const result = await syncDashboardCloudPlansApi();
    syncSummary.value = result;
    message.success(
      `同步完成：${result.summary.region_count} 个地区，${result.summary.after_pricing_count} 条在售规格`,
    );
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '配置同步失败');
  } finally {
    syncing.value = false;
  }
}

function resetSearch() {
  keyword.value = '';
  syncSummary.value = null;
  loadData();
}

onMounted(() => {
  syncSummary.value = null;
  loadData();
});
</script>

<template>
  <Page
    description="这里同步 AWS / 阿里云当前在售主规格与进货价；AWS 已按主套餐口径过滤，不包含 Windows / IPv6 / 优化型变体，也不会生成或修改对外售卖套餐。"
    title="配置同步"
  >
    <Card>
      <template #title>
        <Space>
          <span>主规格与进货价同步</span>
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索地区、厂商、主规格名"
            style="width: 360px"
            @search="loadData"
          />
          <Button
            size="small"
            type="primary"
            :disabled="!canRunCloudDanger"
            :loading="syncing"
            @click="syncPricing"
          >
            同步主规格与进货价
          </Button>
          <Button size="small" @click="resetSearch">重置</Button>
          <Button size="small" @click="loadData">刷新</Button>
        </Space>
      </template>

      <Space direction="vertical" style="width: 100%; margin-bottom: 16px">
        <Card v-if="syncSummary" size="small">
          <Space wrap>
            <Tag color="blue">
              同步地区 {{ syncSummary.summary.region_count }}
            </Tag>
            <Tag color="green">
              主规格 {{ syncSummary.summary.after_pricing_count }}
            </Tag>
            <Tag color="gold">
              人工套餐 {{ syncSummary.summary.after_plan_count }}
            </Tag>
            <Tag>同步结果 {{ syncSummary.synced ? '成功' : '未完成' }}</Tag>
          </Space>
        </Card>
      </Space>

      <Collapse
        v-if="groupedProviders.length > 0"
        :active-key="providerActiveKeys"
        @update:active-key="updateProviderActiveKeys"
      >
        <Collapse.Panel
          v-for="provider in groupedProviders"
          :key="provider.key"
        >
          <template #header>
            <Space>
              <Tag
                :color="provider.key === 'aws_lightsail' ? 'blue' : 'orange'"
              >
                {{ provider.label }}
              </Tag>
              <span>{{ provider.regions.length }} 个地区</span>
            </Space>
          </template>

          <Collapse
            :active-key="getRegionActiveKeys(provider)"
            @update:active-key="
              (keys) => updateRegionActiveKeys(provider.key, keys)
            "
          >
            <Collapse.Panel
              v-for="region in provider.regions"
              :key="`${provider.key}:${region.regionCode}`"
            >
              <template #header>
                <Space>
                  <span>{{ region.regionName }}</span>
                  <Tag>{{ region.regionCode }}</Tag>
                  <Tag color="green">{{ region.pricing.length }} 个主规格</Tag>
                </Space>
              </template>

              <Table
                :columns="pricingColumns"
                :data-source="region.pricing"
                :pagination="false"
                row-key="id"
                size="small"
                :scroll="{ x: 1520 }"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'cost_price'">
                    <Tag>
                      {{ formatMoney(record.cost_price, record.currency) }}
                    </Tag>
                  </template>
                  <template v-else-if="column.key === 'is_active'">
                    <Tag :color="record.is_active ? 'success' : 'default'">
                      {{ record.is_active ? '在售' : '停用' }}
                    </Tag>
                  </template>
                </template>
              </Table>
            </Collapse.Panel>
          </Collapse>
        </Collapse.Panel>
      </Collapse>

      <Empty v-else description="暂无配置同步数据" />
    </Card>
  </Page>
</template>
