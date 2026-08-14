<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { SvgBellIcon, SvgCardIcon, SvgDownloadIcon } from '@vben/icons';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Button, Card, Col, Row, Space, Statistic } from 'ant-design-vue';

import { getDashboardOverviewApi } from '#/api/admin';

const router = useRouter();
const loading = ref(false);
const overview = ref<Awaited<
  ReturnType<typeof getDashboardOverviewApi>
> | null>(null);
const trendChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);

const overviewItems = computed(() => {
  const summary = overview.value?.summary;
  return [
    {
      icon: SvgCardIcon,
      title: '服务器总量',
      totalTitle: '有效代理/服务器',
      totalValue: summary?.server_assets_total ?? 0,
      value: 0,
    },
    {
      icon: SvgDownloadIcon,
      title: '今日到期',
      totalTitle: '今日到期代理',
      totalValue: summary?.due_today ?? 0,
      value: 0,
    },
    {
      icon: SvgBellIcon,
      title: '今日订单',
      totalTitle: '今日新增云订单',
      totalValue: summary?.new_orders_today ?? 0,
      value: 0,
    },
    {
      icon: SvgCardIcon,
      title: '利润统计',
      totalTitle: 'USDT',
      totalValue: Number(summary?.profit_total ?? 0),
      value: 0,
    },
  ];
});

const financeCards = computed(() => {
  const summary = overview.value?.summary;
  return [
    { label: '收入', value: summary?.revenue_total ?? '0', suffix: 'USDT' },
    { label: '成本', value: summary?.cost_total ?? '0', suffix: 'USDT' },
    { label: '利润', value: summary?.profit_total ?? '0', suffix: 'USDT' },
  ];
});

function renderCharts() {
  const charts = overview.value?.charts;
  if (!charts) return;
  renderTrendChart({
    grid: { bottom: 35, containLabel: true, left: 24, right: 56, top: 45 },
    legend: {
      top: 0,
      data: ['用户增长', '订单数量', '服务器数量', '到期数量', '利润'],
    },
    series: [
      {
        name: '用户增长',
        type: 'line',
        smooth: true,
        data: charts.trend.users,
      },
      {
        name: '订单数量',
        type: 'line',
        smooth: true,
        data: charts.trend.orders,
      },
      {
        name: '服务器数量',
        type: 'line',
        smooth: true,
        data: charts.trend.servers,
      },
      {
        name: '到期数量',
        type: 'line',
        smooth: true,
        data: charts.trend.expiry,
      },
      {
        name: '利润',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: charts.trend.profit,
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: { boundaryGap: false, data: charts.trend.labels, type: 'category' },
    yAxis: [
      { min: 0, name: '数量', type: 'value' },
      { min: 0, name: '利润', type: 'value' },
    ],
  });
}

async function loadOverview() {
  loading.value = true;
  try {
    overview.value = await getDashboardOverviewApi();
  } finally {
    loading.value = false;
  }
  await nextTick();
  renderCharts();
  window.setTimeout(renderCharts, 100);
  window.setTimeout(renderCharts, 500);
}

onMounted(loadOverview);
watch(
  () => overview.value?.charts,
  async () => {
    await nextTick();
    renderCharts();
  },
);
</script>

<template>
  <div class="p-5">
    <div
      class="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
    >
      <div>
        <div class="text-2xl font-semibold">分析页</div>
        <div class="mt-1 text-sm text-gray-500">
          横轴固定为当月 1–31
          号；用户增长、订单数量、服务器数量、到期数量和利润每月 1
          号自动从新月份重新统计。
        </div>
      </div>
      <Space>
        <Button @click="router.push('/admin/cloud-orders/list')">云订单</Button>
        <Button type="primary" @click="loadOverview">刷新分析</Button>
      </Space>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card v-for="item in overviewItems" :key="item.title" class="w-full">
        <div class="flex items-start justify-between gap-4">
          <Statistic :title="item.title" :value="item.totalValue" />
          <component
            :is="item.icon"
            class="size-8 shrink-0 text-[var(--ant-color-primary)]"
          />
        </div>
        <div class="mt-2 text-sm text-[var(--ant-color-text-tertiary)]">
          {{ item.totalTitle }}
        </div>
      </Card>
    </div>

    <Row class="mt-5" :gutter="16">
      <Col :span="24">
        <Card
          :loading="loading"
          title="月度趋势图：用户增长 / 订单数量 / 服务器数量 / 到期数量 / 利润"
        >
          <EchartsUI ref="trendChartRef" style="width: 100%; height: 360px" />
        </Card>
      </Col>
    </Row>

    <Row class="mt-5" :gutter="16">
      <Col :span="24">
        <Card :loading="loading" title="利润统计">
          <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card v-for="item in financeCards" :key="item.label" size="small">
              <Statistic
                :title="item.label"
                :value="item.value"
                :suffix="item.suffix"
              />
            </Card>
          </div>
        </Card>
      </Col>
    </Row>
  </div>
</template>
