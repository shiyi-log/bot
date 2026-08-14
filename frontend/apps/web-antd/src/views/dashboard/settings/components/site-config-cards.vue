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
  message,
  Space,
  Switch,
  Tag,
} from 'ant-design-vue';

import {
  getDashboardSiteConfigGroupsApi,
  getDashboardSiteConfigsApi,
  initDashboardSiteConfigsApi,
  updateDashboardSiteConfigApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const props = defineProps<{
  description?: string;
  groupKey: string;
  title: string;
}>();

const loading = ref(false);
const initLoading = ref(false);
const siteConfigs = ref<DashboardSiteConfigItem[]>([]);
const configGroups = ref<DashboardSiteConfigGroup[]>([]);
const savingMap = reactive<Record<string, boolean>>({});
const draftMap = reactive<Record<string, string>>({});
const sensitiveMap = reactive<Record<string, boolean>>({});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const activeGroup = computed(
  () =>
    configGroups.value.find((item) => item.group === props.groupKey) || null,
);
const items = computed(() => activeGroup.value?.items || []);

function syncDrafts() {
  for (const item of items.value) {
    draftMap[item.key] = item.value || '';
    sensitiveMap[item.key] = !!item.is_sensitive;
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

async function initConfigs() {
  if (!requireCloudDangerPermission('初始化配置')) return;
  initLoading.value = true;
  try {
    await initDashboardSiteConfigsApi({ scope: 'configs' });
    message.success('配置项已初始化');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '初始化失败');
  } finally {
    initLoading.value = false;
  }
}

async function saveItem(item: DashboardSiteConfigGroupItem) {
  if (!requireCloudDangerPermission('保存系统配置')) return;
  const current = currentConfig(item);
  if (!current?.id) {
    message.error('该配置尚未初始化，请先点击顶部“初始化配置”');
    return;
  }
  savingMap[item.key] = true;
  try {
    await updateDashboardSiteConfigApi(current.id, {
      is_sensitive: !!sensitiveMap[item.key],
      key: item.key,
      value: draftMap[item.key] ?? '',
    });
    message.success(`已保存：${item.description || item.key}`);
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    savingMap[item.key] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page :description="description || ''" :title="title">
    <Space class="mb-3">
      <Button
        type="primary"
        :disabled="!canRunCloudDanger"
        :loading="initLoading"
        @click="initConfigs"
      >
        初始化配置
      </Button>
      <Button :loading="loading" @click="loadData">刷新</Button>
    </Space>

    <div class="config-grid" v-if="items.length > 0">
      <Card
        v-for="item in items"
        :key="item.key"
        :loading="loading"
        class="config-card"
      >
        <template #title>
          <div class="card-title">{{ item.description || item.key }}</div>
        </template>
        <div class="mb-2 flex items-center gap-2 text-xs text-gray-500">
          <span>键名：{{ item.key }}</span>
          <Tag :color="sensitiveMap[item.key] ? 'orange' : 'default'">
            {{ sensitiveMap[item.key] ? '敏感' : '普通' }}
          </Tag>
        </div>
        <Input.TextArea
          v-model:value="draftMap[item.key]"
          :auto-size="{ minRows: 4, maxRows: 10 }"
          :placeholder="item.value || '请输入配置内容'"
        />
        <div class="mt-3 flex items-center justify-between">
          <Space>
            <span class="text-sm text-gray-500">敏感配置</span>
            <Switch
              v-model:checked="sensitiveMap[item.key]"
              :disabled="!canRunCloudDanger"
            />
          </Space>
          <Button
            type="primary"
            :disabled="!canRunCloudDanger"
            :loading="savingMap[item.key]"
            @click="saveItem(item)"
          >
            保存
          </Button>
        </div>
      </Card>
    </div>

    <Card v-else :loading="loading">
      <div class="text-gray-500">暂无配置项，请先点击“初始化配置”。</div>
    </Card>
  </Page>
</template>

<style scoped>
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.config-card {
  height: 100%;
}

.card-title {
  font-weight: 600;
}
</style>
