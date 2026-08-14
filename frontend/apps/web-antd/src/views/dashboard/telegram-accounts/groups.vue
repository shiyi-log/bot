<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type {
  DashboardTelegramGroupDetail,
  DashboardTelegramGroupFilterItem,
  DashboardTelegramGroupFilterPayload,
  DashboardTelegramGroupMemberItem,
  DashboardTelegramMessageItem,
} from '#/api/admin';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createDashboardTelegramGroupApi,
  getDashboardTelegramGroupDetailApi,
  getDashboardTelegramGroupsApi,
  updateDashboardTelegramGroupApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const keyword = ref('');
const current = ref<DashboardTelegramGroupFilterItem | null>(null);
const groups = ref<DashboardTelegramGroupFilterItem[]>([]);
const showArchived = ref(false);
const details = ref<Record<number, DashboardTelegramGroupDetail>>({});
const detailLoading = ref<Record<number, boolean>>({});
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const form = reactive<DashboardTelegramGroupFilterPayload>({
  archived: false,
  chat_id: '',
  collapsed: false,
  enabled: false,
  push_enabled: false,
  title: '',
  username: '',
});

const columns: TableColumnsType<DashboardTelegramGroupFilterItem> = [
  { title: '群组', key: 'group' },
  { title: '转发给管理员', key: 'enabled', width: 140 },
  { title: '推送', key: 'push_enabled', width: 120 },
  { title: '绑定页显示', key: 'collapsed', width: 140 },
  { title: '归档', key: 'archived', width: 120 },
  { title: '更新时间', key: 'updated_at', width: 190 },
  { title: '操作', key: 'action', width: 100 },
];

const memberColumns: TableColumnsType<DashboardTelegramGroupMemberItem> = [
  { title: '成员', key: 'member' },
  { title: '消息数', dataIndex: 'message_count', width: 100 },
  { title: '最后出现', key: 'last_seen_at', width: 180 },
];

const messageColumns: TableColumnsType<DashboardTelegramMessageItem> = [
  { title: '成员', key: 'sender', width: 220 },
  { title: '内容', key: 'text' },
  { title: '时间', key: 'created_at', width: 180 },
];

const archivedCount = computed(
  () => groups.value.filter((item) => item.archived).length,
);

const visibleGroups = computed(() =>
  showArchived.value
    ? groups.value
    : groups.value.filter((item) => !item.archived),
);

function resetForm() {
  current.value = null;
  form.archived = false;
  form.chat_id = '';
  form.collapsed = false;
  form.enabled = false;
  form.push_enabled = false;
  form.title = '';
  form.username = '';
}

function formatTime(value?: null | string) {
  if (!value) return '-';
  return value.replace('T', ' ').slice(0, 19);
}

function senderLabel(item: DashboardTelegramMessageItem) {
  const name =
    item.first_name_snapshot ||
    item.username_snapshot ||
    String(item.tg_user_id);
  return `${name} (ID: ${item.tg_user_id})`;
}

function messageText(item: DashboardTelegramMessageItem) {
  if (item.text) return item.text;
  return `[${item.content_type || '非文本消息'}]`;
}

async function loadData() {
  loading.value = true;
  try {
    groups.value = await getDashboardTelegramGroupsApi({
      keyword: keyword.value || undefined,
    });
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  if (!requireCloudDangerPermission('保存 Telegram 群组')) return;
  resetForm();
  modalOpen.value = true;
}

function openEdit(item: DashboardTelegramGroupFilterItem) {
  if (!requireCloudDangerPermission('编辑 Telegram 群组')) return;
  current.value = item;
  form.archived = item.archived;
  form.chat_id = item.chat_id;
  form.collapsed = item.collapsed;
  form.enabled = item.enabled;
  form.push_enabled = item.push_enabled;
  form.title = item.title;
  form.username = item.username;
  modalOpen.value = true;
}

async function submitForm() {
  if (
    !requireCloudDangerPermission(
      current.value ? '保存 Telegram 群组' : '新增 Telegram 群组',
    )
  )
    return;
  if (!form.chat_id || !form.title) {
    message.warning('请填写群组 Chat ID 和群组名称');
    return;
  }
  saving.value = true;
  try {
    if (current.value) {
      await updateDashboardTelegramGroupApi(current.value.id, form);
      message.success('群组已更新');
    } else {
      await createDashboardTelegramGroupApi(form);
      message.success('群组已保存');
    }
    modalOpen.value = false;
    await loadData();
  } catch (error: any) {
    message.error(error?.message || '保存失败');
  } finally {
    saving.value = false;
  }
}

async function toggleEnabled(
  item: DashboardTelegramGroupFilterItem,
  enabled: boolean,
) {
  if (!requireCloudDangerPermission('修改群组转发开关')) return;
  const previous = item.enabled;
  item.enabled = enabled;
  try {
    const updated = await updateDashboardTelegramGroupApi(item.id, { enabled });
    Object.assign(item, updated);
    message.success(enabled ? '已开启群组转发' : '已关闭群组转发');
  } catch (error: any) {
    item.enabled = previous;
    message.error(error?.message || '操作失败');
  }
}

async function togglePushEnabled(
  item: DashboardTelegramGroupFilterItem,
  pushEnabled: boolean,
) {
  if (!requireCloudDangerPermission('修改群组推送开关')) return;
  const previous = item.push_enabled;
  item.push_enabled = pushEnabled;
  try {
    const updated = await updateDashboardTelegramGroupApi(item.id, {
      push_enabled: pushEnabled,
    });
    Object.assign(item, updated);
    message.success(pushEnabled ? '已开启群组推送' : '已关闭群组推送');
  } catch (error: any) {
    item.push_enabled = previous;
    message.error(error?.message || '操作失败');
  }
}

async function loadGroupDetail(item: DashboardTelegramGroupFilterItem) {
  if (details.value[item.id] || detailLoading.value[item.id]) return;
  detailLoading.value = { ...detailLoading.value, [item.id]: true };
  try {
    const detail = await getDashboardTelegramGroupDetailApi(item.id);
    details.value = { ...details.value, [item.id]: detail };
  } catch (error: any) {
    message.error(error?.message || '加载群组详情失败');
  } finally {
    detailLoading.value = { ...detailLoading.value, [item.id]: false };
  }
}

function handleExpand(
  expanded: boolean,
  item: DashboardTelegramGroupFilterItem,
) {
  if (expanded) loadGroupDetail(item);
}

async function toggleCollapsed(
  item: DashboardTelegramGroupFilterItem,
  collapsed: boolean,
) {
  if (!requireCloudDangerPermission('修改群组绑定页显示')) return;
  const previous = item.collapsed;
  item.collapsed = collapsed;
  try {
    const updated = await updateDashboardTelegramGroupApi(item.id, {
      collapsed,
    });
    Object.assign(item, updated);
    message.success(collapsed ? '已在绑定页隐藏群组' : '已在绑定页显示群组');
  } catch (error: any) {
    item.collapsed = previous;
    message.error(error?.message || '操作失败');
  }
}

async function toggleArchived(
  item: DashboardTelegramGroupFilterItem,
  archived: boolean,
) {
  if (!requireCloudDangerPermission('修改群组归档状态')) return;
  const previous = item.archived;
  item.archived = archived;
  try {
    const updated = await updateDashboardTelegramGroupApi(item.id, {
      archived,
    });
    Object.assign(item, updated);
    message.success(archived ? '已归档群组' : '已取消归档');
  } catch (error: any) {
    item.archived = previous;
    message.error(error?.message || '操作失败');
  }
}

onMounted(() => loadData());
</script>

<template>
  <Page
    description="控制哪些 Telegram 群组消息允许转发给管理员，以及哪些群组允许监听推送"
    title="群组通知"
  >
    <Card :loading="loading" title="群组通知开关">
      <template #extra>
        <Space>
          <Tag v-if="archivedCount" color="default">
            已归档 {{ archivedCount }}
          </Tag>
          <Switch
            v-model:checked="showArchived"
            checked-children="显示归档"
            un-checked-children="折叠归档"
          />
          <Input.Search
            v-model:value="keyword"
            allow-clear
            enter-button="搜索"
            placeholder="搜索群组名 / 用户名 / Chat ID"
            @search="loadData"
          />
          <Button @click="loadData">刷新</Button>
          <Button
            type="primary"
            :disabled="!canRunCloudDanger"
            @click="openCreate"
          >
            保存群组
          </Button>
        </Space>
      </template>

      <Table
        :columns="columns"
        :data-source="visibleGroups"
        :pagination="false"
        row-key="id"
        size="middle"
        @expand="handleExpand"
      >
        <template #expandedRowRender="{ record }">
          <div class="group-detail">
            <Card
              :loading="
                detailLoading[(record as DashboardTelegramGroupFilterItem).id]
              "
              size="small"
            >
              <div
                v-if="details[(record as DashboardTelegramGroupFilterItem).id]"
                class="detail-grid"
              >
                <div>
                  <div class="detail-title">群成员（按聊天记录聚合）</div>
                  <Table
                    :columns="memberColumns"
                    :data-source="
                      details[(record as DashboardTelegramGroupFilterItem).id]
                        ?.members || []
                    "
                    :pagination="false"
                    row-key="tg_user_id"
                    size="small"
                  >
                    <template
                      #bodyCell="{ column: memberColumn, record: member }"
                    >
                      <template v-if="memberColumn.key === 'member'">
                        <div class="member-name">
                          {{
                            (member as DashboardTelegramGroupMemberItem)
                              .display_label
                          }}
                        </div>
                        <div
                          v-if="
                            (member as DashboardTelegramGroupMemberItem)
                              .username
                          "
                          class="group-meta"
                        >
                          @{{
                            (member as DashboardTelegramGroupMemberItem)
                              .username
                          }}
                        </div>
                      </template>
                      <template v-else-if="memberColumn.key === 'last_seen_at'">
                        {{
                          formatTime(
                            (member as DashboardTelegramGroupMemberItem)
                              .last_seen_at,
                          )
                        }}
                      </template>
                    </template>
                  </Table>
                </div>

                <div>
                  <div class="detail-title">最近聊天记录</div>
                  <Table
                    :columns="messageColumns"
                    :data-source="
                      details[(record as DashboardTelegramGroupFilterItem).id]
                        ?.messages || []
                    "
                    :pagination="false"
                    row-key="id"
                    size="small"
                  >
                    <template
                      #bodyCell="{ column: messageColumn, record: chatMessage }"
                    >
                      <template v-if="messageColumn.key === 'sender'">
                        {{
                          senderLabel(
                            chatMessage as DashboardTelegramMessageItem,
                          )
                        }}
                      </template>
                      <template v-else-if="messageColumn.key === 'text'">
                        <span class="message-text">
                          {{
                            messageText(
                              chatMessage as DashboardTelegramMessageItem,
                            )
                          }}
                        </span>
                      </template>
                      <template v-else-if="messageColumn.key === 'created_at'">
                        {{
                          formatTime(
                            (chatMessage as DashboardTelegramMessageItem)
                              .created_at,
                          )
                        }}
                      </template>
                    </template>
                  </Table>
                </div>
              </div>
              <div v-else class="empty-detail">
                暂无群成员或聊天记录。只要个人号监听收到该群消息，就会在这里出现。
              </div>
            </Card>
          </div>
        </template>

        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'group'">
            <div class="group-title">
              {{
                (record as DashboardTelegramGroupFilterItem).title ||
                (record as DashboardTelegramGroupFilterItem).chat_id
              }}
            </div>
            <div class="group-meta">
              <Tag
                v-if="(record as DashboardTelegramGroupFilterItem).username"
                color="blue"
              >
                @{{ (record as DashboardTelegramGroupFilterItem).username }}
              </Tag>
              <span>
                ID {{ (record as DashboardTelegramGroupFilterItem).chat_id }}
              </span>
            </div>
          </template>
          <template v-else-if="column.key === 'enabled'">
            <Switch
              :checked="(record as DashboardTelegramGroupFilterItem).enabled"
              checked-children="开启"
              :disabled="!canRunCloudDanger"
              un-checked-children="关闭"
              @change="
                (checked) =>
                  toggleEnabled(
                    record as DashboardTelegramGroupFilterItem,
                    Boolean(checked),
                  )
              "
            />
          </template>
          <template v-else-if="column.key === 'push_enabled'">
            <Switch
              :checked="
                (record as DashboardTelegramGroupFilterItem).push_enabled
              "
              checked-children="开启"
              :disabled="!canRunCloudDanger"
              un-checked-children="关闭"
              @change="
                (checked) =>
                  togglePushEnabled(
                    record as DashboardTelegramGroupFilterItem,
                    Boolean(checked),
                  )
              "
            />
          </template>
          <template v-else-if="column.key === 'collapsed'">
            <Switch
              :checked="!(record as DashboardTelegramGroupFilterItem).collapsed"
              checked-children="显示"
              :disabled="!canRunCloudDanger"
              un-checked-children="隐藏"
              @change="
                (checked) =>
                  toggleCollapsed(
                    record as DashboardTelegramGroupFilterItem,
                    !Boolean(checked),
                  )
              "
            />
          </template>
          <template v-else-if="column.key === 'archived'">
            <Switch
              :checked="(record as DashboardTelegramGroupFilterItem).archived"
              checked-children="归档"
              :disabled="!canRunCloudDanger"
              un-checked-children="正常"
              @change="
                (checked) =>
                  toggleArchived(
                    record as DashboardTelegramGroupFilterItem,
                    Boolean(checked),
                  )
              "
            />
          </template>
          <template v-else-if="column.key === 'updated_at'">
            {{
              formatTime(
                (record as DashboardTelegramGroupFilterItem).updated_at,
              )
            }}
          </template>
          <template v-else-if="column.key === 'action'">
            <Button
              type="link"
              :disabled="!canRunCloudDanger"
              @click="openEdit(record as DashboardTelegramGroupFilterItem)"
            >
              编辑
            </Button>
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="modalOpen"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: !canRunCloudDanger }"
      :title="current ? '编辑群组' : '保存群组'"
      @ok="submitForm"
    >
      <Form layout="vertical">
        <Form.Item label="群组 Chat ID" required>
          <Input
            v-model:value="form.chat_id"
            :disabled="!!current"
            placeholder="例如 -1001234567890"
          />
        </Form.Item>
        <Form.Item label="群组名称" required>
          <Input v-model:value="form.title" placeholder="请输入群组名称" />
        </Form.Item>
        <Form.Item label="群组用户名">
          <Input
            v-model:value="form.username"
            placeholder="可选，例如 groupname"
          />
        </Form.Item>
        <Form.Item label="转发给管理员">
          <Switch
            v-model:checked="form.enabled"
            checked-children="开启"
            :disabled="!canRunCloudDanger"
            un-checked-children="关闭"
          />
        </Form.Item>
        <Form.Item label="Bark 推送">
          <Switch
            v-model:checked="form.push_enabled"
            checked-children="开启"
            :disabled="!canRunCloudDanger"
            un-checked-children="关闭"
          />
        </Form.Item>
        <Form.Item label="在绑定页显示">
          <Switch
            :checked="!form.collapsed"
            checked-children="显示"
            :disabled="!canRunCloudDanger"
            un-checked-children="隐藏"
            @change="(checked) => (form.collapsed = !Boolean(checked))"
          />
        </Form.Item>
        <Form.Item label="归档">
          <Switch
            v-model:checked="form.archived"
            checked-children="归档"
            :disabled="!canRunCloudDanger"
            un-checked-children="正常"
          />
        </Form.Item>
      </Form>
    </Modal>
  </Page>
</template>

<style scoped>
.group-title {
  font-weight: 600;
}

.group-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
  color: hsl(var(--muted-foreground));
}

.group-detail {
  padding: 8px 24px;
  background: hsl(var(--muted) / 30%);
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.8fr) minmax(360px, 1.2fr);
  gap: 16px;
}

.detail-title {
  margin-bottom: 8px;
  font-weight: 600;
}

.member-name {
  font-weight: 500;
}

.message-text {
  display: inline-block;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-detail {
  color: hsl(var(--muted-foreground));
}
</style>
