import { requestClient } from '#/api/request';

export interface BotSettings {
  telegram_api_hash_configured: boolean;
  telegram_api_hash_preview: string;
  telegram_api_id: string;
  tron_api_key_configured: boolean;
  tron_api_key_env_var: string;
  tron_api_key_preview: string;
  tron_api_key?: string;
  tron_api_url: string;
  tron_monitor_enabled: boolean;
  tron_poll_interval: number;
  updated_at: null | string;
}

export interface BotSettingsUpdate {
  telegram_api_hash?: string;
  telegram_api_id?: string;
  tron_api_key?: string;
  tron_api_key_env_var: string;
  tron_api_url: string;
  tron_monitor_enabled: boolean;
  tron_poll_interval: number;
}

export interface TelegramListQuery {
  bot?: number;
  enabled?: boolean;
  group?: number;
  page?: number;
  page_size?: number;
  search?: string;
}

export interface DrfPaginatedResponse<T> {
  count: number;
  next: null | string;
  previous: null | string;
  results: T[];
}

export interface TelegramUser {
  first_name: string;
  first_seen_at: null | string;
  id: number;
  is_active: boolean;
  is_bot: boolean;
  language_code: string;
  last_name: string;
  last_seen_at: null | string;
  message_count: number;
  telegram_id: number | string;
  username: string;
}

export interface TelegramGroup {
  first_seen_at: null | string;
  group_type: 'channel' | 'group' | 'supergroup' | string;
  id: number;
  is_active: boolean;
  last_seen_at: null | string;
  message_count: number;
  member_count: number;
  telegram_id: number | string;
  title: string;
  username: string;
}

export interface TelegramGroupMember {
  bot: number;
  bot_name: string;
  first_name: string;
  first_spoke_at: string;
  group: number;
  group_telegram_id: number | string;
  group_title: string;
  id: number;
  last_name: string;
  last_spoke_at: string;
  message_count: number;
  telegram_user_id: number | string;
  user: number;
  username: string;
}

export interface TelegramBot {
  button_count: number;
  clone_count: number;
  clone_enabled: boolean;
  cloned_from: null | number;
  created_at: string;
  credential_configured: boolean;
  enabled: boolean;
  id: number;
  name: string;
  telegram_id: null | number | string;
  token_env_var: string;
  updated_at: string;
  username: string;
  welcome_enabled: boolean;
  welcome_message: string;
}

export interface TelegramBotClonePayload {
  billing_plan?: string;
  name?: string;
  token_env_var?: string;
}

export interface TelegramBotCloneResult extends TelegramBot {
  billing: {
    message: string;
    plan: string;
    provider: string;
    status: 'reserved';
  };
}

export interface TelegramBotPayload {
  clone_enabled: boolean;
  enabled: boolean;
  name: string;
  telegram_id: null | number | string;
  token_env_var: string;
  username: string;
  welcome_enabled: boolean;
  welcome_message: string;
}

export interface TelegramBotButton {
  bot: number;
  bot_name: string;
  created_at: string;
  enabled: boolean;
  id: number;
  position: number;
  row: number;
  text: string;
  updated_at: string;
  url: string;
}

export interface TelegramBotButtonPayload {
  bot: number;
  enabled: boolean;
  position: number;
  row: number;
  text: string;
  url: string;
}

export type TelegramLoginAccountStatus =
  | 'code_sent'
  | 'error'
  | 'logged_in'
  | 'password_required'
  | 'pending'
  | 'session_expired';

export interface TelegramLoginAccount {
  created_at: string;
  first_name: string;
  has_session: boolean;
  id: number;
  label: string;
  last_checked_at: null | string;
  last_error: string;
  last_name: string;
  phone: string;
  status: TelegramLoginAccountStatus;
  telegram_id: null | number | string;
  updated_at: string;
  username: string;
}

export type TelegramLoginAccountPage =
  DrfPaginatedResponse<TelegramLoginAccount>;

export interface TelegramLoginStartPayload {
  label?: string;
  phone: string;
}

export interface TelegramLoginCodePayload {
  account_id: number;
  code: string;
}

export interface TelegramLoginPasswordPayload {
  account_id: number;
  password: string;
}

export interface TelegramLoginStartResult {
  account: TelegramLoginAccount;
  account_id: number;
  next_step: 'code';
}

export interface TelegramLoginCodeResult {
  account: TelegramLoginAccount;
  account_id: number;
  next_step: 'complete' | 'password';
}

export interface TelegramLoginPasswordResult {
  account: TelegramLoginAccount;
  account_id: number;
  next_step: 'complete';
}

export interface TronAddress {
  address: string;
  balance_sun: number;
  usdt_balance_sun: number;
  created_at: string;
  enabled: boolean;
  id: number;
  label: string;
  last_checked_at: null | string;
  last_error: string;
  last_transaction_id: string;
  status: 'error' | 'ok' | 'pending';
  updated_at: string;
}

export interface TronAddressPayload {
  address: string;
  enabled: boolean;
  label: string;
}

export function getBotSettingsApi() {
  return requestClient.get<BotSettings>('/settings/');
}

export function updateBotSettingsApi(payload: BotSettingsUpdate) {
  return requestClient.request<BotSettings>('/settings/', {
    data: payload,
    method: 'PATCH',
  });
}

export function getTelegramUsersApi(params: TelegramListQuery) {
  return requestClient.get<DrfPaginatedResponse<TelegramUser>>('/users/', {
    params,
  });
}

export function getTelegramGroupsApi(params: TelegramListQuery) {
  return requestClient.get<DrfPaginatedResponse<TelegramGroup>>('/groups/', {
    params,
  });
}

export function getTelegramGroupMembersApi(params: TelegramListQuery) {
  return requestClient.get<DrfPaginatedResponse<TelegramGroupMember>>(
    '/members/',
    { params },
  );
}

export function getTelegramBotsApi(params: TelegramListQuery = {}) {
  return requestClient.get<DrfPaginatedResponse<TelegramBot>>('/bots/', {
    params,
  });
}

export function createTelegramBotApi(payload: TelegramBotPayload) {
  return requestClient.post<TelegramBot>('/bots/', payload);
}

export function updateTelegramBotApi(id: number, payload: TelegramBotPayload) {
  return requestClient.request<TelegramBot>(`/bots/${id}/`, {
    data: payload,
    method: 'PATCH',
  });
}

export function cloneTelegramBotApi(
  id: number,
  payload: TelegramBotClonePayload = {},
) {
  return requestClient.post<TelegramBotCloneResult>(
    `/bots/${id}/clone/`,
    payload,
  );
}

export function deleteTelegramBotApi(id: number) {
  return requestClient.delete(`/bots/${id}/`);
}

export function getTelegramBotButtonsApi(params: TelegramListQuery = {}) {
  return requestClient.get<DrfPaginatedResponse<TelegramBotButton>>(
    '/bot-buttons/',
    { params },
  );
}

export function createTelegramBotButtonApi(payload: TelegramBotButtonPayload) {
  return requestClient.post<TelegramBotButton>('/bot-buttons/', payload);
}

export function updateTelegramBotButtonApi(
  id: number,
  payload: TelegramBotButtonPayload,
) {
  return requestClient.request<TelegramBotButton>(`/bot-buttons/${id}/`, {
    data: payload,
    method: 'PATCH',
  });
}

export function deleteTelegramBotButtonApi(id: number) {
  return requestClient.delete(`/bot-buttons/${id}/`);
}

export function getTelegramLoginAccountsApi(params: TelegramListQuery = {}) {
  return requestClient.get<TelegramLoginAccountPage>('/telegram-accounts/', {
    params,
  });
}

export function deleteTelegramLoginAccountApi(id: number) {
  return requestClient.delete(`/telegram-accounts/${id}/`);
}

export function startTelegramLoginApi(payload: TelegramLoginStartPayload) {
  return requestClient.post<TelegramLoginStartResult>(
    '/telegram-accounts/login/start/',
    payload,
    { timeout: 180_000 },
  );
}

export function submitTelegramLoginCodeApi(payload: TelegramLoginCodePayload) {
  return requestClient.post<TelegramLoginCodeResult>(
    '/telegram-accounts/login/code/',
    payload,
    { timeout: 180_000 },
  );
}

export function submitTelegramLoginPasswordApi(
  payload: TelegramLoginPasswordPayload,
) {
  return requestClient.post<TelegramLoginPasswordResult>(
    '/telegram-accounts/login/password/',
    payload,
    { timeout: 180_000 },
  );
}

export function checkTelegramLoginAccountApi(id: number) {
  return requestClient.post<TelegramLoginAccount>(
    `/telegram-accounts/${id}/check/`,
  );
}

export function getTronAddressesApi(params: TelegramListQuery) {
  return requestClient.get<DrfPaginatedResponse<TronAddress>>(
    '/tron/addresses/',
    { params },
  );
}

export function createTronAddressApi(payload: TronAddressPayload) {
  return requestClient.post<TronAddress>('/tron/addresses/', payload);
}

export function updateTronAddressApi(id: number, payload: TronAddressPayload) {
  return requestClient.request<TronAddress>(`/tron/addresses/${id}/`, {
    data: payload,
    method: 'PATCH',
  });
}

export function checkTronAddressApi(id: number) {
  return requestClient.post<TronAddress>(`/tron/addresses/${id}/check/`);
}

export function deleteTronAddressApi(id: number) {
  return requestClient.delete(`/tron/addresses/${id}/`);
}
