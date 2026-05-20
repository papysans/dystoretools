ALLOWED_TABLES = {
    "doudian_order",
    "doudian_goods",
    "doudian_stock",
    "doudian_sku_diagnose",
    "goods_diagnose",
    "doudian_comment",
    "comment_tag_stat",
    "comment_index_warn",
    "neg_comment_product",
    "doudian_aftersale",
    "aftersale_counts",
    "member_dashboard_agg",
    "member_dashboard_day",
    "member_dashboard_hist",
    "audience_feature",
    "member_sales_activity",
    "compass_core_data",
    "compass_core_trend",
    "compass_diagnose",
    "compass_industry_word",
    "compass_shop_rank",
    "shop_video",
    "experience_score",
    "shop_violation",
    "marketing_coupon",
    "marketing_activity",
    "logistics_event",
    "content_video",
    "content_live",
    "content_imagetext",
    "peer_shop",
    "peer_goods",
    "peer_livestream",
}

FORBIDDEN_TABLES = {
    "llm_provider",
    "llm_model",
    "chat_conversation",
    "chat_message",
    "app_setting",
    "session_event",
    "alert",
    "scrape_task_run",
    "ai_generation",
    "alembic_version",
    "information_schema",
    "mysql",
    "performance_schema",
    "sys",
}

PII_COLUMNS = {
    "order_sn",
    "receiver_phone",
    "receiver_mobile",
    "receiver_address",
    "receiver_name",
    "buyer_nick",
    "user_nick",
    "phone",
    "mobile",
    "address",
    "name",
}


def is_allowed_table(name: str) -> bool:
    lowered = name.lower()
    if lowered in FORBIDDEN_TABLES or lowered.startswith("chat_"):
        return False
    return lowered in ALLOWED_TABLES
