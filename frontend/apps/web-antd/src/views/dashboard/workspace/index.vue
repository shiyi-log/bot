<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Button, Card, Col, Empty, Row, Tag } from 'ant-design-vue';
import dayjs from 'dayjs';

import { getDashboardOverviewApi } from '#/api/admin';

const router = useRouter();
const loading = ref(false);
const overview = ref<Awaited<
  ReturnType<typeof getDashboardOverviewApi>
> | null>(null);

const expiryPlans = computed(() => overview.value?.shutdown_logs || []);
const unattachedIpDeletePlans = computed(
  () => overview.value?.unattached_ip_delete_plans || [],
);

function planItemKey(item: {
  asset_id?: null | number;
  asset_name?: null | string;
  id?: null | number;
  plan_item_key?: null | string;
  public_ip?: null | string;
  source_id?: null | number;
  source_kind?: null | string;
}) {
  return (
    item.plan_item_key ||
    (item.source_kind && item.source_id
      ? `${item.source_kind}:${item.source_id}`
      : '') ||
    item.asset_id ||
    item.id ||
    item.public_ip ||
    item.asset_name ||
    'unknown'
  );
}

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function expiryColor(value?: null | string) {
  if (!value) return 'default';
  const hours = dayjs(value).diff(dayjs(), 'hour');
  if (hours <= 0) return 'red';
  if (hours <= 24) return 'volcano';
  if (hours <= 72) return 'orange';
  if (hours <= 7 * 24) return 'gold';
  if (hours <= 30 * 24) return 'blue';
  return 'green';
}

function accountText(item: {
  account_label?: string;
  cloud_account_id?: null | number;
  external_account_id?: string;
}) {
  return (
    item.external_account_id ||
    item.account_label ||
    (item.cloud_account_id ? `#${item.cloud_account_id}` : '')
  );
}

function openPlanDetail(item: {
  asset_id?: null | number;
  detail_path?: string;
  order_id?: null | number;
}) {
  if (item.detail_path) {
    router.push(item.detail_path).catch(() => {});
    return;
  }
  if (item.asset_id) {
    router.push(`/admin/cloud-assets/${item.asset_id}`).catch(() => {});
    return;
  }
  if (item.order_id) {
    router.push(`/admin/cloud-orders/${item.order_id}`).catch(() => {});
    return;
  }
  router.push('/admin/cloud-assets').catch(() => {});
}

function statusColor(status?: string, isOldShutdown = false) {
  if (isOldShutdown) return 'default';
  if (['deleted', 'failed'].includes(status || '')) return 'red';
  if (['expired', 'suspended'].includes(status || '')) return 'volcano';
  if (['renew_pending', 'stopped'].includes(status || '')) return 'orange';
  if (['pending', 'starting', 'stopping'].includes(status || '')) return 'blue';
  if (['completed', 'paid', 'running'].includes(status || '')) return 'green';
  return 'purple';
}

async function loadOverview() {
  loading.value = true;
  try {
    overview.value = await getDashboardOverviewApi();
  } finally {
    loading.value = false;
  }
}

onMounted(loadOverview);
</script>

<template>
  <div class="p-5">
    <div>
      <Row :gutter="[16, 20]">
        <Col :xl="16" :lg="15" :span="24">
          <Card
            class="h-full"
            :loading="loading"
            title="最近到期 / 生命周期主链"
          >
            <template #extra>
              <Button
                size="small"
                type="link"
                @click="router.push('/admin/logs/servers')"
              >
                查看全部
              </Button>
            </template>
            <div v-if="expiryPlans.length > 0" class="space-y-4">
              <div
                v-for="item in expiryPlans"
                :key="item.id"
                class="rounded-lg border border-[var(--ant-color-border-secondary)] p-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div
                    class="flex flex-wrap items-center gap-2 font-medium leading-8"
                  >
                    <Tag>{{ item.public_ip || '-' }}</Tag>
                    <span>{{ item.order_no }}</span>
                    <Tag
                      v-if="
                        item.user_display_name &&
                        item.user_display_name !== '未绑定用户'
                      "
                      color="blue"
                    >
                      {{ item.user_display_name }}
                      {{
                        item.username_label && item.username_label !== '-'
                          ? item.username_label
                          : ''
                      }}
                    </Tag>
                    <Tag color="purple">
                      {{ item.provider_label || item.provider || '-' }}
                    </Tag>
                    <Tag v-if="accountText(item)" color="geekblue">
                      账号 {{ accountText(item) }}
                    </Tag>
                  </div>
                  <div class="flex items-center gap-2">
                    <Tag
                      :color="statusColor(item.status, item.is_old_shutdown)"
                    >
                      {{ item.status_label || item.status || '-' }}
                    </Tag>
                    <Button
                      size="small"
                      type="link"
                      @click="openPlanDetail(item)"
                    >
                      详细
                    </Button>
                  </div>
                </div>
                <div
                  class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm leading-8"
                >
                  <span>
                    到期：
                    <Tag :color="expiryColor(item.actual_expires_at)">
                      {{ formatTime(item.actual_expires_at) }}
                    </Tag>
                  </span>
                  <span>
                    关机：
                    <Tag :color="expiryColor(item.suspend_at)">
                      {{ formatTime(item.suspend_at) }}
                    </Tag>
                  </span>
                  <span>
                    删机：
                    <Tag :color="expiryColor(item.delete_at)">
                      {{ formatTime(item.delete_at) }}
                    </Tag>
                  </span>
                </div>
              </div>
            </div>
            <Empty v-else description="暂无生命周期计划" />
          </Card>
        </Col>
        <Col :xl="8" :lg="9" :span="24">
          <Card class="h-full" :loading="loading" title="未附加IP删除计划">
            <div v-if="unattachedIpDeletePlans.length > 0" class="space-y-4">
              <div
                v-for="item in unattachedIpDeletePlans"
                :key="planItemKey(item)"
                class="rounded-lg border border-[var(--ant-color-border-secondary)] p-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div
                    class="flex flex-wrap items-center gap-2 font-medium leading-8"
                  >
                    <Tag>{{ item.public_ip || '-' }}</Tag>
                    <Button
                      size="small"
                      type="link"
                      @click="openPlanDetail(item)"
                    >
                      {{ item.asset_name }}
                    </Button>
                  </div>
                  <Tag
                    :color="
                      item.is_overdue ? 'red' : expiryColor(item.delete_at)
                    "
                  >
                    {{ item.provider_status || '未附加IP' }}
                  </Tag>
                </div>
                <div
                  class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm leading-8"
                >
                  <span>过期时间：</span>
                  <Tag :color="expiryColor(item.actual_expires_at)">
                    {{ formatTime(item.actual_expires_at) }}
                  </Tag>
                  <span>删除时间：</span>
                  <Tag :color="expiryColor(item.delete_at)">
                    {{ formatTime(item.delete_at) }}
                  </Tag>
                  <Tag
                    v-if="
                      item.user_display_name &&
                      item.user_display_name !== '未绑定用户'
                    "
                    color="blue"
                  >
                    {{ item.user_display_name }}
                    {{
                      item.username_label && item.username_label !== '-'
                        ? item.username_label
                        : ''
                    }}
                  </Tag>
                </div>
              </div>
            </div>
            <Empty v-else description="暂无未附加IP删除计划" />
          </Card>
        </Col>
      </Row>
    </div>
  </div>
</template>
