<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardCloudAccountConfigItem,
  DashboardCloudAccountCreatePayload,
} from '#/api/admin';

import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Form,
  Input,
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
  createDashboardCloudAccountApi,
  deleteDashboardCloudAccountApi,
  getDashboardCloudAccountsApi,
  updateDashboardCloudAccountApi,
  verifyDashboardCloudAccountApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const open = ref(false);
const current = ref<DashboardCloudAccountConfigItem | null>(null);
const items = ref<DashboardCloudAccountConfigItem[]>([]);
const togglingMap = reactive<Record<number, boolean>>({});
const provisionTogglingMap = reactive<Record<number, boolean>>({});

const DEFAULT_REGION_MAP: Record<string, string> = {
  aliyun: 'cn-hongkong',
  aws: 'ap-southeast-1',
};

const form = reactive<DashboardCloudAccountCreatePayload>({
  access_key: '',
  external_account_id: '',
  is_active: true,
  name: '',
  provision_enabled: true,
  provider: 'aws',
  region_hint: '',
  secret_key: '',
});

const regionHintTouched = ref(false);

const effectiveRegionHint = computed(() => {
  return String(form.region_hint || DEFAULT_REGION_MAP[form.provider] || '');
});

const regionHintPlaceholder = computed(() => {
  return DEFAULT_REGION_MAP[form.provider] || '请输入默认地区';
});

const regionHintValue = computed({
  get: () => form.region_hint ?? '',
  set: (value: number | string) => {
    regionHintTouched.value = true;
    form.region_hint = String(value || '');
  },
});

const columns: TableColumnsType<DashboardCloudAccountConfigItem> = [
  {
    title: '云厂商',
    dataIndex: 'provider_label',
    key: 'provider_label',
    width: 120,
  },
  { title: '备注', dataIndex: 'name', key: 'name', width: 160 },
  {
    title: '账号ID',
    dataIndex: 'external_account_id',
    key: 'external_account_id',
    width: 180,
  },
  {
    title: '默认地区',
    dataIndex: 'effective_region',
    key: 'region_hint',
    width: 140,
  },
  {
    title: 'Access Key',
    dataIndex: 'access_key_preview',
    key: 'access_key_preview',
    width: 180,
  },
  {
    title: 'Secret Key',
    dataIndex: 'secret_key_preview',
    key: 'secret_key_preview',
    width: 180,
  },
  { title: '巡检状态', dataIndex: 'status', key: 'status', width: 120 },
  {
    title: '状态说明',
    dataIndex: 'status_note',
    key: 'status_note',
    width: 260,
  },
  {
    title: '创建服务器',
    dataIndex: 'provision_enabled',
    key: 'provision_enabled',
    width: 120,
  },
  { title: '启用', dataIndex: 'is_active', key: 'is_active', width: 80 },
  { title: '操作', key: 'actions', width: 280, fixed: 'right' as const },
];

function resetForm() {
  form.access_key = '';
  form.external_account_id = '';
  form.is_active = true;
  form.name = '';
  form.provision_enabled = true;
  form.provider = 'aws';
  form.region_hint = '';
  form.secret_key = '';
  regionHintTouched.value = false;
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardCloudAccountsApi();
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireCloudDangerPermission('添加云账号')) return;
  current.value = null;
  resetForm();
  open.value = true;
}

function openEdit(record: DashboardCloudAccountConfigItem) {
  if (!requireCloudDangerPermission('编辑云账号')) return;
  current.value = record;
  form.access_key = '';
  form.external_account_id = record.external_account_id || '';
  form.is_active = !!record.is_active;
  form.name = record.name || '';
  form.provision_enabled = record.provision_enabled !== false;
  form.provider = record.provider || 'aws';
  form.region_hint = record.region_hint || '';
  form.secret_key = '';
  regionHintTouched.value = !!record.region_hint;
  open.value = true;
}

watch(
  () => form.provider,
  () => {
    if (!regionHintTouched.value || !String(form.region_hint || '').trim()) {
      form.region_hint = '';
    }
  },
);

async function save() {
  if (!requireCloudDangerPermission('保存云账号')) return;
  saving.value = true;
  try {
    const payload: Partial<DashboardCloudAccountCreatePayload> = {
      ...form,
      region_hint: effectiveRegionHint.value || null,
    };
    if (current.value) {
      if (!String(payload.access_key || '').trim()) delete payload.access_key;
      if (!String(payload.secret_key || '').trim()) delete payload.secret_key;
      await updateDashboardCloudAccountApi(current.value.id, payload);
      message.success('云账号已更新');
    } else {
      await createDashboardCloudAccountApi(
        payload as DashboardCloudAccountCreatePayload,
      );
      message.success('云账号已创建');
    }
    open.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

function openDetail(record: DashboardCloudAccountConfigItem) {
  router.push(`/admin/cloud-accounts/${record.id}`).catch(() => {});
}

async function verify(record: DashboardCloudAccountConfigItem) {
  if (!requireCloudDangerPermission('验证云账号')) return;
  try {
    const result = await verifyDashboardCloudAccountApi(record.id, {
      region: record.effective_region || record.region_hint || undefined,
    });
    message.success(
      `验证成功：${result.region}，实例数 ${result.instance_count}`,
    );
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '验证失败');
  }
}

async function toggleActive(
  record: DashboardCloudAccountConfigItem,
  checked: boolean,
) {
  if (!requireCloudDangerPermission('切换云账号启用状态')) return;
  togglingMap[record.id] = true;
  try {
    await updateDashboardCloudAccountApi(record.id, { is_active: checked });
    record.is_active = checked;
    message.success(checked ? '云账号已启用' : '云账号已停用');
  } catch (error: any) {
    record.is_active = !checked;
    message.error(error?.message || '切换失败');
  } finally {
    togglingMap[record.id] = false;
  }
}

async function toggleProvision(
  record: DashboardCloudAccountConfigItem,
  checked: boolean,
) {
  if (!requireCloudDangerPermission('切换云账号创建服务器权限')) return;
  provisionTogglingMap[record.id] = true;
  try {
    await updateDashboardCloudAccountApi(record.id, {
      provision_enabled: checked,
    });
    record.provision_enabled = checked;
    message.success(
      checked ? '已允许使用该账号创建服务器' : '已停止使用该账号创建服务器',
    );
  } catch (error: any) {
    record.provision_enabled = !checked;
    message.error(error?.message || '切换失败');
  } finally {
    provisionTogglingMap[record.id] = false;
  }
}

async function remove(record: DashboardCloudAccountConfigItem) {
  if (!requireCloudDangerPermission('删除云账号')) return;
  try {
    await deleteDashboardCloudAccountApi(record.id);
    message.success('云账号已删除');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '删除失败');
  }
}

onMounted(loadData);
</script>

<template>
  <Page description="支持多平台、多账户并行管理" title="云账号设置">
    <div class="cloud-account-toolbar">
      <Button type="primary" :disabled="!canRunCloudDanger" @click="openCreate">
        添加账号
      </Button>
      <Button :loading="loading" @click="loadData">刷新</Button>
    </div>

    <Table
      :columns="columns"
      :data-source="items"
      :loading="loading"
      row-key="id"
      :pagination="false"
      :scroll="{ x: 1520 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'provision_enabled'">
          <Switch
            :checked="
              (record as DashboardCloudAccountConfigItem).provision_enabled !==
              false
            "
            checked-children="允许"
            :disabled="!canRunCloudDanger"
            :loading="
              provisionTogglingMap[
                (record as DashboardCloudAccountConfigItem).id
              ]
            "
            un-checked-children="禁用"
            @change="
              (checked) =>
                toggleProvision(
                  record as DashboardCloudAccountConfigItem,
                  Boolean(checked),
                )
            "
          />
        </template>
        <template v-else-if="column.key === 'is_active'">
          <Switch
            :checked="(record as DashboardCloudAccountConfigItem).is_active"
            checked-children="启用"
            :disabled="!canRunCloudDanger"
            :loading="
              togglingMap[(record as DashboardCloudAccountConfigItem).id]
            "
            un-checked-children="停用"
            @change="
              (checked) =>
                toggleActive(
                  record as DashboardCloudAccountConfigItem,
                  Boolean(checked),
                )
            "
          />
        </template>
        <template v-else-if="column.key === 'status'">
          <Tag
            :color="
              record.status === 'ok'
                ? 'success'
                : record.status === 'error'
                  ? 'error'
                  : 'default'
            "
          >
            {{ record.status_label || record.status || '待检查' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <Space>
            <Button
              type="link"
              size="small"
              @click="openDetail(record as DashboardCloudAccountConfigItem)"
            >
              详情
            </Button>
            <Button
              type="link"
              size="small"
              :disabled="!canRunCloudDanger"
              @click="verify(record as DashboardCloudAccountConfigItem)"
            >
              验证
            </Button>
            <Button
              type="link"
              size="small"
              :disabled="!canRunCloudDanger"
              @click="openEdit(record as DashboardCloudAccountConfigItem)"
            >
              编辑
            </Button>
            <Popconfirm
              title="确认删除该云账号吗？"
              @confirm="remove(record as DashboardCloudAccountConfigItem)"
            >
              <Button
                danger
                type="link"
                size="small"
                :disabled="!canRunCloudDanger"
              >
                删除
              </Button>
            </Popconfirm>
          </Space>
        </template>
      </template>
    </Table>

    <Modal
      v-model:open="open"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      :title="current ? '编辑云账号' : '添加云账号'"
      @ok="save"
    >
      <Form layout="vertical">
        <Form.Item label="云平台">
          <Select
            v-model:value="form.provider"
            :options="[
              { label: 'AWS', value: 'aws' },
              { label: '阿里云', value: 'aliyun' },
            ]"
          />
        </Form.Item>
        <Form.Item label="账号备注">
          <Input
            v-model:value="form.name"
            placeholder="例如：11 / 嗷嗷 / 生产 AWS"
          />
        </Form.Item>
        <Form.Item label="云厂商账号ID">
          <Input
            v-model:value="form.external_account_id"
            placeholder="例如：121241；留空时验证账号后自动回填（AWS 支持）"
          />
        </Form.Item>
        <Form.Item label="默认地区">
          <Input
            v-model:value="regionHintValue"
            :placeholder="regionHintPlaceholder"
          />
          <div class="text-xs text-[var(--ant-color-text-description)] mt-1">
            未填写时自动使用：{{ effectiveRegionHint }}
          </div>
        </Form.Item>
        <Form.Item label="Access Key">
          <Input
            v-model:value="form.access_key"
            :placeholder="current ? '留空则不修改' : 'Access Key'"
          />
        </Form.Item>
        <Form.Item label="Secret Key">
          <Input.Password
            v-model:value="form.secret_key"
            :placeholder="current ? '留空则不修改' : 'Secret Key'"
            :visibility-toggle="false"
          />
        </Form.Item>
        <Form.Item label="启用状态">
          <Switch v-model:checked="form.is_active" />
        </Form.Item>
        <Form.Item label="允许创建服务器">
          <Switch v-model:checked="form.provision_enabled" />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.cloud-account-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  margin-bottom: 16px;
}
</style>
