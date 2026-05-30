import { getJSON, postJSON } from "./client";

export interface QcAuthStatus {
  authorized: boolean;
  uid: string | null;
  access_expires_at: string | null;
  refresh_expires_at: string | null;
  advertiser_count: number;
}

export interface QcAdvertiser {
  advertiser_id: string;
  advertiser_name: string | null;
  enabled: boolean;
}

export interface QcReportRow {
  advertiser_id: string;
  stat_date: string;
  level?: string;
  object_id?: string;
  cost: number | null;
  show_cnt: number | null;
  click_cnt: number | null;
  convert_cnt: number | null;
  convert_cost: number | null;
  ctr: number | null;
  pay_order_amount: number | null;
  roi: number | null;
}

export function qcAuthStatus() {
  return getJSON<QcAuthStatus>("/qianchuan/auth/status");
}

export function qcAuthUrl() {
  return getJSON<{ configured: boolean; authorize_url: string | null }>("/qianchuan/auth/url");
}

// authCodeOrUrl 既可是纯 auth_code，也可是整条回调 URL（后端会自动解析出 auth_code）
export function qcExchangeAuthCode(authCodeOrUrl: string) {
  return postJSON<{ uid: string; advertiser_count: number }>("/qianchuan/auth/exchange", { auth_code: authCodeOrUrl });
}

export function qcListAdvertisers() {
  return getJSON<QcAdvertiser[]>("/qianchuan/advertisers");
}

export function qcSync(days = 7) {
  return postJSON<{ advertisers: number; rows: number; failed?: number }>("/qianchuan/sync", { days });
}

export function qcReport(advertiserId?: string, days = 30) {
  return getJSON<QcReportRow[]>("/qianchuan/report", { advertiser_id: advertiserId, days });
}
