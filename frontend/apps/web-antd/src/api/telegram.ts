import { requestClient } from '#/api/request';

export interface BotSettings {
  bot_enabled: boolean;
  tron_monitor_enabled: boolean;
  tron_poll_interval: number;
  updated_at: null | string;
  welcome_enabled: boolean;
  welcome_message: string;
}

export type BotSettingsUpdate = Omit<BotSettings, 'updated_at'>;

export interface TelegramListQuery {
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

export interface TronAddress {
  address: string;
  balance_sun: number;
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

export function deleteTronAddressApi(id: number) {
  return requestClient.delete(`/tron/addresses/${id}/`);
}
