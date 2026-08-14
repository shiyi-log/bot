<script lang="ts" setup>
import type {
  DashboardSiteConfigGroup,
  DashboardSiteConfigGroupItem,
  DashboardSiteConfigItem,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  InputNumber,
  message,
  Modal,
  RadioGroup,
  Space,
} from 'ant-design-vue';

import {
  getDashboardSiteConfigGroupsApi,
  getDashboardSiteConfigsApi,
  initDashboardTextConfigsApi,
  updateDashboardSiteConfigApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const initLoading = ref(false);
const initOpen = ref(false);
const initMode = ref<'missing_only' | 'reset_defaults'>('missing_only');
const siteConfigs = ref<DashboardSiteConfigItem[]>([]);
const configGroups = ref<DashboardSiteConfigGroup[]>([]);
const savingMap = reactive<Record<string, boolean>>({});
const draftMap = reactive<Record<string, string>>({});
const sortOrderMap = reactive<Record<string, number>>({});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const textItems = computed(() => {
  const group = configGroups.value.find((item) => item.group === 'custom_text');
  return group?.items || [];
});

function syncDrafts() {
  for (const item of textItems.value) {
    draftMap[item.key] = item.value || item.default_value || '';
    sortOrderMap[item.key] = Number(item.sort_order || 0);
  }
}

async function loadData() {
  loading.value = true;
  try {
    const [configs, groups] = await Promise.all([
      getDashboardSiteConfigsApi(),
      getDashboardSiteConfigGroupsApi(),
    ]);
    siteConfigs.value = configs;
    configGroups.value = groups;
    syncDrafts();
  } finally {
    loading.value = false;
  }
}

function currentConfig(item: DashboardSiteConfigGroupItem) {
  return siteConfigs.value.find((config) => config.key === item.key) || null;
}

async function saveItem(item: DashboardSiteConfigGroupItem) {
  if (!requireCloudDangerPermission('保存文案配置')) return;
  const current = currentConfig(item);
  if (!current?.id) {
    message.error('该文案尚未初始化，请先点击顶部“初始化文案”');
    return;
  }
  savingMap[item.key] = true;
  try {
    await updateDashboardSiteConfigApi(current.id, {
      is_sensitive: !!item.is_sensitive,
      key: item.key,
      value: draftMap[item.key] ?? '',
      sort_order: Number(sortOrderMap[item.key] || 0),
    });
    message.success(`已保存：${item.description || item.key}`);
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    savingMap[item.key] = false;
  }
}

function resetItem(item: DashboardSiteConfigGroupItem) {
  if (!requireCloudDangerPermission('恢复默认文案')) return;
  draftMap[item.key] = item.default_value || '';
}

async function initTexts() {
  if (!requireCloudDangerPermission('初始化文案配置')) return;
  initLoading.value = true;
  try {
    const result = await initDashboardTextConfigsApi({ mode: initMode.value });
    message.success(
      `初始化完成：新增 ${result.created} 项，更新 ${result.updated} 项`,
    );
    initOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '初始化文案失败');
  } finally {
    initLoading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page
    description="初始化方案 + 人工干预方案并存：可先自动铺默认文案，再逐条人工调整"
    title="文案设置"
  >
    <Space class="mb-3">
      <Button
        type="primary"
        :disabled="!canRunCloudDanger"
        :loading="initLoading"
        @click="initOpen = true"
      >
        初始化文案
      </Button>
      <Button :loading="loading" @click="loadData">刷新</Button>
    </Space>

    <div class="text-grid" v-if="textItems.length > 0">
      <Card
        v-for="item in textItems"
        :key="item.key"
        :loading="loading"
        class="text-card"
      >
        <template #title>
          <div class="card-title">{{ item.description || item.key }}</div>
        </template>
        <Input.TextArea
          v-model:value="draftMap[item.key]"
          :auto-size="{ minRows: 4, maxRows: 8 }"
          :placeholder="item.default_value || '请输入文案内容'"
        />
        <div class="mt-2 text-xs text-gray-400">
          默认文案：{{ item.default_value || '-' }}
        </div>
        <div class="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <span>排序</span>
          <InputNumber
            v-model:value="sortOrderMap[item.key]"
            :min="0"
            :precision="0"
            size="small"
            style="width: 110px"
          />
          <span class="text-gray-400">数值越小越靠前</span>
        </div>
        <Space class="mt-3">
          <Button
            :loading="savingMap[item.key]"
            :disabled="!canRunCloudDanger"
            type="primary"
            @click="saveItem(item)"
          >
            保存
          </Button>
          <Button :disabled="!canRunCloudDanger" @click="resetItem(item)">
            恢复默认
          </Button>
        </Space>
      </Card>
    </div>

    <Card v-else :loading="loading">
      <div class="text-gray-500">暂无文案项，请先点击“初始化文案”。</div>
    </Card>

    <Modal
      v-model:open="initOpen"
      title="初始化文案"
      :confirm-loading="initLoading"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      @ok="initTexts"
    >
      <div class="mb-3 text-sm text-gray-500">
        支持两套方案：只补缺失/空值，或强制重置为默认文案。
      </div>
      <RadioGroup
        v-model:value="initMode"
        :options="[
          { label: '只补缺失和空值（推荐）', value: 'missing_only' },
          { label: '强制重置为默认文案', value: 'reset_defaults' },
        ]"
      />
    </Modal>
  </Page>
</template>

<style scoped>
.text-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.text-card {
  height: 100%;
}

.card-title {
  font-weight: 600;
}
</style>
