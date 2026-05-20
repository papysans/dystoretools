"""Aftersale enum mappings. Mirror of web/src/api/enums.ts — keep in sync until OpenAPI codegen lands."""

AFTERSALE_TYPE: dict[int, str] = {
    0: "退款",
    1: "退货",
    3: "换货",
}

AFTERSALE_STATUS: dict[int, str] = {
    6: "待审核",
    7: "进行中",
    11: "已完成",
    27: "已关闭",
}

# Canonical 18 aftersale dimensions per docs/api-catalog.md §6 lines 117-122.
AFTERSALE_CANONICAL_DIMS: tuple[str, ...] = (
    "all_audit_reg_spill",
    "approaching_deadline_audit",
    "urge_audit",
    "presale_all_audit",
    "refund_audit",
    "return_audit",
    "exchange_audit",
    "resend_audit",
    "repair_audit",
    "wait_for_receive_and_delivery",
    "return_for_receive",
    "exchange_for_receive",
    "wait_user_delivery",
    "wait_user_sign",
    "exchange_wait_user_sign",
    "arbitrate_pending_negotiation",
    "arbitrate_pending_evidence",
    "arbitrate_pending",
)
