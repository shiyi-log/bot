<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardAdminUserItem,
  DashboardAdminUserUpsertPayload,
} from '#/api/admin';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  changeDashboardMyPasswordApi,
  createDashboardAdminUserApi,
  deleteDashboardAdminUserApi,
  getDashboardAdminUsersApi,
  updateDashboardAdminUserApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const passwordSaving = ref(false);
const open = ref(false);
const current = ref<DashboardAdminUserItem | null>(null);
const items = ref<DashboardAdminUserItem[]>([]);
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const form = reactive<DashboardAdminUserUpsertPayload>({
  email: '',
  is_active: true,
  is_superuser: false,
  password: '',
  username: '',
});

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
});

const columns: TableColumnsType<DashboardAdminUserItem> = [
  { title: '用户名', dataIndex: 'username', key: 'username', width: 180 },
  { title: '邮箱', dataIndex: 'email', key: 'email', width: 220 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 90 },
  {
    title: '超级管理员',
    dataIndex: 'is_superuser',
    key: 'is_superuser',
    width: 110,
  },
  { title: '最近登录', dataIndex: 'last_login', key: 'last_login', width: 180 },
  { title: '操作', key: 'actions', width: 180 },
];

function resetForm() {
  form.email = '';
  form.is_active = true;
  form.is_superuser = false;
  form.password = '';
  form.username = '';
}

async function loadData() {
  loading.value = true;
  try {
    items.value = await getDashboardAdminUsersApi();
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireCloudDangerPermission('添加管理员')) return;
  current.value = null;
  resetForm();
  open.value = true;
}

function openEdit(record: DashboardAdminUserItem) {
  if (!requireCloudDangerPermission('编辑管理员')) return;
  current.value = record;
  form.email = record.email || '';
  form.is_active = !!record.is_active;
  form.is_superuser = !!record.is_superuser;
  form.password = '';
  form.username = record.username;
  open.value = true;
}

async function save() {
  if (
    !requireCloudDangerPermission(current.value ? '保存管理员' : '添加管理员')
  ) {
    return;
  }
  saving.value = true;
  try {
    if (current.value) {
      const payload: DashboardAdminUserUpsertPayload = {
        email: form.email,
        is_active: form.is_active,
        is_superuser: form.is_superuser,
        username: form.username,
      };
      if (form.password) {
        payload.password = form.password;
      }
      await updateDashboardAdminUserApi(current.value.id, payload);
      message.success('管理员已更新');
    } else {
      await createDashboardAdminUserApi(form);
      message.success('管理员已创建');
    }
    open.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

async function remove(record: DashboardAdminUserItem) {
  if (!requireCloudDangerPermission('删除管理员')) return;
  try {
    await deleteDashboardAdminUserApi(record.id);
    message.success('管理员已删除');
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '删除失败');
  }
}

async function savePassword() {
  passwordSaving.value = true;
  try {
    await changeDashboardMyPasswordApi({ ...passwordForm });
    message.success('密码修改成功，请重新登录');
    passwordForm.old_password = '';
    passwordForm.new_password = '';
    passwordForm.confirm_password = '';
  } catch (error: any) {
    message.error(error?.message || '密码修改失败');
  } finally {
    passwordSaving.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <Page description="管理员账号管理与当前登录账号密码修改" title="管理员设置">
    <Card class="mb-4" title="管理员列表">
      <template #extra>
        <Space>
          <Button
            type="primary"
            :disabled="!canRunCloudDanger"
            @click="openCreate"
          >
            添加管理员
          </Button>
          <Button :loading="loading" @click="loadData">刷新</Button>
        </Space>
      </template>

      <Table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        row-key="id"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'is_active'">
            <Tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '启用' : '停用' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'is_superuser'">
            <Tag :color="record.is_superuser ? 'blue' : 'default'">
              {{ record.is_superuser ? '是' : '否' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space>
              <Button
                type="link"
                size="small"
                :disabled="!canRunCloudDanger"
                @click="openEdit(record as DashboardAdminUserItem)"
              >
                编辑
              </Button>
              <Popconfirm
                title="确认删除该管理员吗？"
                @confirm="remove(record as DashboardAdminUserItem)"
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
    </Card>

    <Card title="我的密码修改" style="max-width: 640px">
      <Form layout="vertical">
        <Form.Item label="旧密码">
          <Input.Password
            v-model:value="passwordForm.old_password"
            :visibility-toggle="true"
            placeholder="请输入旧密码"
          />
        </Form.Item>
        <Form.Item label="新密码">
          <Input.Password
            v-model:value="passwordForm.new_password"
            :visibility-toggle="true"
            placeholder="请输入新密码"
          />
        </Form.Item>
        <Form.Item label="确认新密码">
          <Input.Password
            v-model:value="passwordForm.confirm_password"
            :visibility-toggle="true"
            placeholder="再次输入新密码"
          />
        </Form.Item>
        <Button type="primary" :loading="passwordSaving" @click="savePassword">
          保存新密码
        </Button>
      </Form>
    </Card>

    <Modal
      v-model:open="open"
      :confirm-loading="saving"
      :title="current ? '编辑管理员' : '添加管理员'"
      @ok="save"
    >
      <Form layout="vertical">
        <Form.Item label="用户名">
          <Input v-model:value="form.username" placeholder="管理员用户名" />
        </Form.Item>
        <Form.Item label="邮箱">
          <Input v-model:value="form.email" placeholder="邮箱（可选）" />
        </Form.Item>
        <Form.Item :label="current ? '新密码（留空不改）' : '密码'">
          <Input.Password
            v-model:value="form.password"
            :placeholder="current ? '留空不修改密码' : '请输入密码'"
            :visibility-toggle="true"
          />
        </Form.Item>
        <Form.Item label="启用状态">
          <Switch v-model:checked="form.is_active" />
        </Form.Item>
        <Form.Item label="超级管理员">
          <Switch v-model:checked="form.is_superuser" />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>
