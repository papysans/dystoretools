/**
 * Single source of truth for aftersale enum mappings.
 * Backend mirror: backend/dystore/api/v1/_enums.py — keep in sync until OpenAPI codegen lands.
 * Values verified from doudian_aftersale DB samples on 2026-05-20.
 */

export const AFTERSALE_TYPE: Record<number, string> = {
  0: "退款",
  1: "退货",
  3: "换货",
};

export const AFTERSALE_STATUS: Record<number, string> = {
  6: "待审核",
  7: "进行中",
  11: "已完成",
  27: "已关闭",
};

export const AFTERSALE_STATUS_COLOR: Record<number, string> = {
  6: "orange",
  7: "blue",
  11: "green",
  27: "default",
};

export type AftersaleTypeCode = keyof typeof AFTERSALE_TYPE;
export type AftersaleStatusCode = keyof typeof AFTERSALE_STATUS;
