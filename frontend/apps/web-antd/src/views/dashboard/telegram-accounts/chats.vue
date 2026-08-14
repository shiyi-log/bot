<script lang="ts" setup>
import type {
  DashboardTelegramChatUserItem,
  DashboardTelegramMessageItem,
} from '#/api/admin';

import { computed, nextTick, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Avatar,
  Button,
  Empty,
  Input,
  message,
  Switch,
  Tag,
} from 'ant-design-vue';

import {
  getDashboardTelegramAccountsApi,
  getDashboardTelegramMessagesApi,
  sendDashboardTelegramMessageApi,
} from '#/api/admin';
import { useDashboardPermissions } from '#/utils/dashboard-permissions';

const loading = ref(false);
const sending = ref(false);
const keyword = ref('');
const draftMessage = ref('');
const showEmptyUsers = ref(false);
const users = ref<DashboardTelegramChatUserItem[]>([]);
const messages = ref<DashboardTelegramMessageItem[]>([]);
const selectedUser = ref<DashboardTelegramChatUserItem | null>(null);
const messageScrollRef = ref<HTMLElement | null>(null);
const { canRunCloudDanger, requireCloudDangerPermission } =
  useDashboardPermissions();

const orderedMessages = computed(() => [...messages.value].toReversed());
const usersWithMessagesCount = computed(
  () => users.value.filter((item) => item.message_count > 0).length,
);
const usersWithoutMessagesCount = computed(
  () => users.value.filter((item) => item.message_count <= 0).length,
);
const totalMessagesCount = computed(() =>
  users.value.reduce((sum, item) => sum + (item.message_count || 0), 0),
);

const visibleUsers = computed(() => {
  const items = [...users.value].toSorted((a, b) => {
    const aHasMessages = a.message_count > 0 ? 1 : 0;
    const bHasMessages = b.message_count > 0 ? 1 : 0;
    if (aHasMessages !== bHasMessages) return bHasMessages - aHasMessages;
    return String(b.latest_at || '').localeCompare(String(a.latest_at || ''));
  });
  if (showEmptyUsers.value) return items;
  return items.filter((item) => item.message_count > 0);
});

const timelineGroups = computed(() => {
  const groups: Array<{
    items: DashboardTelegramMessageItem[];
    key: string;
    label: string;
  }> = [];
  for (const item of orderedMessages.value) {
    const key = (item.created_at || '').slice(0, 10) || 'unknown';
    let group = groups[groups.length - 1];
    if (!group || group.key !== key) {
      group = {
        key,
        label: formatGroupDate(item.created_at),
        items: [],
      };
      groups.push(group);
    }
    group.items.push(item);
  }
  return groups;
});

async function scrollMessagesToBottom() {
  await nextTick();
  const el = messageScrollRef.value;
  if (el) el.scrollTop = el.scrollHeight;
}

async function loadData(options: { keepSelected?: boolean } = {}) {
  loading.value = true;
  const currentTgUserId = selectedUser.value?.tg_user_id;
  try {
    const overview = await getDashboardTelegramAccountsApi({
      keyword: keyword.value || undefined,
      scope: 'users',
    });
    users.value = overview.users || [];
    if (options.keepSelected && currentTgUserId) {
      selectedUser.value =
        users.value.find((item) => item.tg_user_id === currentTgUserId) ||
        selectedUser.value;
    } else {
      selectedUser.value = null;
      messages.value = [];
    }
  } finally {
    loading.value = false;
  }
}

async function selectUser(user: DashboardTelegramChatUserItem) {
  selectedUser.value = user;
  loading.value = true;
  try {
    messages.value = await getDashboardTelegramMessagesApi({
      tg_user_id: user.tg_user_id,
    });
    await scrollMessagesToBottom();
  } finally {
    loading.value = false;
  }
}

async function sendMessage() {
  if (!requireCloudDangerPermission('发送 Telegram 消息')) return;
  const text = draftMessage.value.trim();
  if (!selectedUser.value || !text) return;
  const user = selectedUser.value;
  if (!user.latest_chat_id) {
    message.error('该用户暂无可回复会话');
    return;
  }
  sending.value = true;
  try {
    const sent = await sendDashboardTelegramMessageApi({
      chat_id: user.latest_chat_id,
      login_account_id: user.latest_login_account_id,
      text,
    });
    messages.value = [
      sent,
      ...messages.value.filter((item) => item.id !== sent.id),
    ];
    draftMessage.value = '';
    await loadData({ keepSelected: true });
    await scrollMessagesToBottom();
  } catch (error: any) {
    message.error(error?.message || '发送失败');
  } finally {
    sending.value = false;
  }
}

function messagePeerText(item: DashboardTelegramMessageItem) {
  if (item.direction === 'out') return '客服';
  if (item.username_snapshot) return `@${item.username_snapshot}`;
  if (item.first_name_snapshot) return item.first_name_snapshot;
  return `ID ${item.tg_user_id}`;
}

function userInitial(user: DashboardTelegramChatUserItem | null) {
  const name =
    user?.display_name?.trim() || user?.primary_username?.trim() || '?';
  return name.slice(0, 1).toUpperCase();
}

function messageInitial(item: DashboardTelegramMessageItem) {
  return messagePeerText(item).replace(/^@/, '').slice(0, 1).toUpperCase();
}

function formatTime(value?: null | string) {
  if (!value) return '-';
  return value.replace('T', ' ').slice(0, 16);
}

function formatShortTime(value?: null | string) {
  if (!value) return '--:--';
  return value.slice(11, 16);
}

function formatGroupDate(value?: null | string) {
  if (!value) return '未知日期';
  return value.slice(0, 10).replaceAll('-', '.');
}

function previewText(user: DashboardTelegramChatUserItem) {
  if (user.latest_message) return user.latest_message;
  return user.message_count > 0 ? '有消息，但最后一条为空' : '暂无聊天记录';
}

onMounted(() => loadData());
</script>

<template>
  <Page title="聊天记录">
    <div class="chat-shell">
      <aside class="conversation-pane">
        <div class="conversation-head">
          <div>
            <div class="conversation-kicker">Telegram Inbox</div>
            <div class="conversation-heading">会话队列</div>
          </div>
          <Button
            class="refresh-button"
            :loading="loading"
            @click="() => loadData({ keepSelected: true })"
          >
            刷新
          </Button>
        </div>

        <div class="pane-summary">
          <div class="summary-item summary-active">
            <span class="summary-label">活跃</span>
            <strong>{{ usersWithMessagesCount }}</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">消息</span>
            <strong>{{ totalMessagesCount }}</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">空用户</span>
            <strong>{{ usersWithoutMessagesCount }}</strong>
          </div>
        </div>

        <div class="pane-toolbar">
          <div class="chat-search-row">
            <Input
              v-model:value="keyword"
              allow-clear
              placeholder="搜索用户 / 昵称 / Telegram ID"
              @press-enter="() => loadData()"
            />
            <Button type="primary" @click="() => loadData()">搜索</Button>
          </div>
          <div class="pane-actions">
            <label class="switch-line">
              <Switch v-model:checked="showEmptyUsers" size="small" />
              <span>显示 0 消息用户</span>
            </label>
          </div>
        </div>

        <div class="conversation-list">
          <div
            v-for="user in visibleUsers"
            :key="user.tg_user_id"
            class="conversation-item"
            :class="{ active: selectedUser?.tg_user_id === user.tg_user_id }"
            @click="selectUser(user)"
          >
            <Avatar class="conversation-avatar" :size="44">
              {{ userInitial(user) }}
            </Avatar>
            <div class="conversation-main">
              <div class="conversation-title-row">
                <span class="conversation-title">{{ user.display_name }}</span>
                <Tag
                  v-if="selectedUser?.tg_user_id === user.tg_user_id"
                  color="green"
                >
                  当前
                </Tag>
                <Tag v-else-if="user.message_count > 0" color="blue">
                  活跃
                </Tag>
                <Tag v-else color="default"> 空白 </Tag>
              </div>
              <div class="conversation-subtitle">
                {{ user.username_label || `ID ${user.tg_user_id}` }}
              </div>
              <div class="conversation-preview">
                {{ previewText(user) }}
              </div>
            </div>
            <div class="conversation-side">
              <span class="conversation-count">{{ user.message_count }}</span>
              <span class="conversation-time">{{
                formatTime(user.latest_at)
              }}</span>
            </div>
          </div>
          <Empty v-if="visibleUsers.length === 0" description="无活跃会话" />
        </div>
      </aside>

      <section class="chat-pane">
        <header class="chat-header">
          <template v-if="selectedUser">
            <div class="chat-header-main">
              <Avatar class="chat-avatar" :size="54">
                {{ userInitial(selectedUser) }}
              </Avatar>
              <div>
                <div class="chat-kicker">当前会话</div>
                <div class="chat-title">{{ selectedUser.display_name }}</div>
                <div class="chat-subtitle">
                  {{
                    selectedUser.username_label ||
                    `ID ${selectedUser.tg_user_id}`
                  }}
                </div>
              </div>
            </div>
            <div class="chat-header-meta">
              <div class="meta-pill">
                <span class="meta-pill-label">消息</span>
                <strong>{{ selectedUser.message_count }}</strong>
              </div>
              <div class="meta-pill">
                <span class="meta-pill-label">最近</span>
                <strong>{{ formatTime(selectedUser.latest_at) }}</strong>
              </div>
            </div>
          </template>
          <template v-else>
            <div>
              <div class="chat-kicker">等待选择</div>
              <div class="chat-title">请选择一个用户</div>
            </div>
          </template>
        </header>

        <main ref="messageScrollRef" class="message-timeline">
          <template v-if="selectedUser && timelineGroups.length > 0">
            <section
              v-for="group in timelineGroups"
              :key="group.key"
              class="timeline-group"
            >
              <div class="timeline-date">
                <span>{{ group.label }}</span>
              </div>
              <div
                v-for="item in group.items"
                :key="item.id"
                class="message-row"
                :class="
                  item.direction === 'out'
                    ? 'message-row-out'
                    : 'message-row-in'
                "
              >
                <Avatar
                  v-if="item.direction !== 'out'"
                  class="message-avatar"
                  :size="32"
                >
                  {{ messageInitial(item) }}
                </Avatar>
                <div
                  class="message-bubble"
                  :class="
                    item.direction === 'out'
                      ? 'message-bubble-out'
                      : 'message-bubble-in'
                  "
                >
                  <div class="message-topline">
                    <span class="message-sender">{{
                      messagePeerText(item)
                    }}</span>
                    <span
                      class="message-source"
                      :class="
                        item.direction === 'out'
                          ? 'message-source-out'
                          : 'message-source-in'
                      "
                    >
                      {{ item.direction === 'out' ? '已回复' : '收到' }}
                    </span>
                    <Tag
                      v-if="item.content_type !== 'text'"
                      class="message-source"
                      color="gold"
                    >
                      {{ item.content_type }}
                    </Tag>
                  </div>
                  <div class="message-content">
                    {{ item.text || `[${item.content_type}]` }}
                  </div>
                  <div class="message-time">
                    {{ formatShortTime(item.created_at) }} ·
                    {{ item.source_label || item.source }}
                  </div>
                </div>
              </div>
            </section>
          </template>
          <Empty
            v-else
            :description="selectedUser ? '暂无聊天记录' : '未选择用户'"
          />
        </main>

        <footer class="message-editor">
          <div class="editor-caption">
            {{ selectedUser ? '回复将发送到最近会话' : '先选择左侧会话' }}
          </div>
          <div class="message-editor-main">
            <Input.TextArea
              v-model:value="draftMessage"
              :auto-size="{ minRows: 2, maxRows: 5 }"
              :disabled="!selectedUser || !canRunCloudDanger"
              placeholder="输入回复内容"
              @press-enter.exact.prevent="sendMessage"
            />
            <Button
              type="primary"
              :disabled="
                !selectedUser || !draftMessage.trim() || !canRunCloudDanger
              "
              :loading="sending"
              @click="sendMessage"
            >
              发送回复
            </Button>
          </div>
        </footer>
      </section>
    </div>
  </Page>
</template>

<style scoped>
.chat-shell {
  --chat-accent: #3b82f6;
  --chat-accent-soft: #0b2a4a;
  --chat-border: #263244;
  --chat-ink: #eef4ff;
  --chat-muted: #94a3b8;
  --chat-panel: #0b1120;
  --chat-shell-bg: #05070d;
  --chat-soft: #0f172a;
  --chat-success: #22c55e;
  --chat-warm: #f59e0b;

  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 14px;
  height: calc(100vh - 206px);
  min-height: 520px;
  padding: 10px;
  margin-top: 10px;
  background:
    linear-gradient(90deg, rgb(59 130 246 / 10%), transparent 38%),
    radial-gradient(circle at 75% 8%, rgb(59 130 246 / 13%), transparent 34%),
    var(--chat-shell-bg);
  border: 1px solid #1f2937;
  border-radius: 8px;
}

.conversation-pane,
.chat-pane {
  display: flex;
  min-height: 0;
  overflow: hidden;
  color: var(--chat-ink);
  background: var(--chat-panel);
  border: 1px solid var(--chat-border);
  border-radius: 8px;
  box-shadow: 0 18px 44px rgb(0 0 0 / 36%);
}

.conversation-pane {
  flex-direction: column;
}

.conversation-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  background: #070b14;
  border-bottom: 1px solid #263243;
}

.conversation-kicker,
.chat-kicker {
  margin-bottom: 3px;
  font-size: 11px;
  font-weight: 700;
  color: #6f86a8;
  text-transform: uppercase;
}

.conversation-heading {
  font-size: 18px;
  font-weight: 800;
  color: #fff;
}

.refresh-button {
  color: #dce6f5;
  background: rgb(255 255 255 / 6%);
  border-color: rgb(148 163 184 / 22%);
}

.refresh-button:hover {
  color: #fff;
  background: rgb(59 130 246 / 16%);
  border-color: rgb(96 165 250 / 42%);
}

.pane-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  padding: 1px;
  background: #1f2a3b;
  border-bottom: 1px solid var(--chat-border);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px 14px 11px;
  background: #0f172a;
}

.summary-item strong {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--chat-ink);
}

.summary-label {
  font-size: 12px;
  color: var(--chat-muted);
}

.summary-active strong {
  color: var(--chat-success);
}

.pane-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 14px 12px;
  background: var(--chat-soft);
  border-bottom: 1px solid var(--chat-border);
}

.pane-toolbar :deep(.ant-input),
.pane-toolbar :deep(.ant-btn),
.message-editor-main :deep(.ant-input) {
  border-radius: 7px;
}

.pane-toolbar :deep(.ant-input),
.message-editor-main :deep(.ant-input) {
  color: var(--chat-ink);
  background: #111827;
  border-color: #334155;
}

.chat-search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.chat-search-row :deep(.ant-input) {
  height: 36px;
  background: transparent;
}

.chat-search-row :deep(.ant-input-affix-wrapper) {
  height: 36px;
  color: var(--chat-ink);
  background: #111827 !important;
  border-color: #334155;
  border-radius: 7px;
  box-shadow: none;
}

.chat-search-row :deep(.ant-input-affix-wrapper:hover),
.chat-search-row :deep(.ant-input-affix-wrapper-focused) {
  border-color: #60a5fa;
}

.chat-search-row :deep(.ant-input-clear-icon) {
  color: #94a3b8;
}

.chat-search-row :deep(.ant-input::placeholder) {
  color: #64748b;
}

.chat-search-row :deep(.ant-btn) {
  height: 36px;
  padding: 0 14px;
  font-weight: 700;
}

.pane-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.switch-line {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--chat-muted);
}

.conversation-list {
  flex: 1;
  min-height: 0;
  padding: 10px;
  overflow: auto;
  background: #070b14;
}

.conversation-item {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 76px;
  gap: 11px;
  align-items: start;
  padding: 12px 10px;
  margin-bottom: 8px;
  cursor: pointer;
  background: #0f172a;
  border: 1px solid #223047;
  border-radius: 8px;
  transition:
    box-shadow 0.18s ease,
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease;
}

.conversation-item:hover,
.conversation-item.active {
  background: #122033;
  border-color: #3b82f6;
  box-shadow: 0 12px 24px rgb(0 0 0 / 24%);
  transform: translateY(-1px);
}

.conversation-item.active {
  border-left: 4px solid var(--chat-accent);
}

.conversation-avatar,
.chat-avatar,
.message-avatar {
  flex: none;
  color: #fff;
  background: #2f6fbd;
}

.conversation-main {
  min-width: 0;
}

.conversation-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
  margin-bottom: 3px;
}

.conversation-title,
.conversation-subtitle,
.conversation-preview {
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-title {
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--chat-ink);
  white-space: nowrap;
}

.conversation-subtitle {
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--chat-muted);
  white-space: nowrap;
}

.conversation-preview {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  font-size: 13px;
  line-height: 1.45;
  color: #cbd5e1;
  -webkit-box-orient: vertical;
}

.conversation-side {
  display: flex;
  flex-direction: column;
  gap: 7px;
  align-items: flex-end;
  font-size: 11px;
  color: var(--chat-muted);
}

.conversation-count {
  min-width: 34px;
  padding: 3px 8px;
  font-weight: 700;
  line-height: 1.2;
  color: #dbeafe;
  text-align: center;
  background: #17243a;
  border-radius: 999px;
}

.conversation-time {
  line-height: 1.35;
  text-align: right;
}

.chat-pane {
  position: relative;
  flex-direction: column;
  background: var(--chat-panel);
}

.chat-header {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  min-height: 86px;
  padding: 16px 18px;
  background: #0b1120;
  border-bottom: 1px solid var(--chat-border);
}

.chat-header-main {
  display: flex;
  gap: 14px;
  align-items: center;
  min-width: 0;
}

.chat-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--chat-ink);
}

.chat-subtitle {
  margin-top: 4px;
  color: var(--chat-muted);
}

.chat-header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 126px;
  padding: 9px 11px;
  background: #111827;
  border: 1px solid #263244;
  border-radius: 8px;
}

.meta-pill-label {
  font-size: 11px;
  color: var(--chat-muted);
  text-transform: uppercase;
}

.message-timeline {
  flex: 1;
  min-height: 0;
  padding: 24px 28px 26px;
  overflow: auto;
  background:
    linear-gradient(rgb(148 163 184 / 8%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(148 163 184 / 8%) 1px, transparent 1px), #05070d;
  background-size: 32px 32px;
}

.timeline-group + .timeline-group {
  margin-top: 18px;
}

.timeline-date {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 10px 0 16px;
}

.timeline-date span {
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 700;
  color: #cbd5e1;
  text-transform: uppercase;
  background: #0f172a;
  border: 1px solid var(--chat-border);
  border-radius: 999px;
  box-shadow: 0 8px 18px rgb(0 0 0 / 28%);
}

.message-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.message-row-in {
  justify-content: flex-start;
}

.message-row-out {
  justify-content: flex-end;
}

.message-bubble {
  min-width: 210px;
  max-width: min(680px, 76%);
  padding: 11px 13px 9px;
  border: 1px solid #263244;
  border-radius: 10px;
  box-shadow: 0 14px 28px rgb(0 0 0 / 28%);
}

.message-bubble-in {
  background: #111827;
  border-bottom-left-radius: 4px;
}

.message-bubble-out {
  color: #eaf2ff;
  background: #0f3154;
  border-color: #1d4f83;
  border-bottom-right-radius: 4px;
}

.message-topline {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
  margin-bottom: 7px;
}

.message-sender {
  font-size: 12px;
  font-weight: 700;
  color: var(--chat-ink);
}

.message-source {
  margin-inline-end: 0;
}

span.message-source {
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.45;
  border-radius: 999px;
}

.message-source-in {
  color: #cbd5e1;
  background: #243044;
}

.message-source-out {
  color: #bfdbfe;
  background: #17365c;
}

.message-content {
  font-size: 15px;
  line-height: 1.62;
  color: #e5e7eb;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.message-time {
  margin-top: 10px;
  font-size: 11px;
  color: var(--chat-muted);
  text-align: right;
}

.message-editor {
  padding: 10px 14px 14px;
  background: #0b1120;
  border-top: 1px solid var(--chat-border);
}

.editor-caption {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--chat-muted);
}

.message-editor-main {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.message-editor-main :deep(.ant-btn) {
  min-width: 92px;
  height: 54px;
  font-weight: 700;
  border-radius: 7px;
}

.message-editor-main :deep(.ant-btn[disabled]) {
  color: #64748b;
  background: #111827;
  border-color: #334155;
}

.message-editor-main :deep(.ant-input) {
  border-radius: 6px;
}

.message-editor-main :deep(.ant-input[disabled]) {
  color: #64748b;
  background: #111827 !important;
  border-color: #334155;
}

.message-editor-main :deep(textarea.ant-input) {
  min-height: 58px;
  resize: none;
}

.message-editor-main :deep(textarea.ant-input[disabled]) {
  color: #64748b;
  background: #111827 !important;
  border-color: #334155;
}

@media (max-width: 1320px) {
  .chat-shell {
    grid-template-columns: 340px minmax(0, 1fr);
  }
}

@media (max-width: 1100px) {
  .chat-shell {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 0;
  }

  .chat-pane {
    scroll-margin-top: 92px;
  }

  .chat-header {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .chat-header-main {
    flex: 1;
  }

  .chat-title {
    line-height: 1.35;
    overflow-wrap: anywhere;
    white-space: normal;
  }

  .chat-header-meta {
    width: 100%;
  }

  .meta-pill {
    flex: 1;
    min-width: 0;
  }

  .conversation-list,
  .message-timeline {
    max-height: 520px;
  }

  .message-timeline {
    padding: 18px 18px 22px;
  }

  .message-bubble {
    min-width: 0;
    max-width: 82%;
  }

  .message-editor {
    grid-template-columns: 1fr;
  }
}
</style>
