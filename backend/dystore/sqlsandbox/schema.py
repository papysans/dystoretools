from __future__ import annotations

from dystore.sqlsandbox.policy import ALLOWED_TABLES, FORBIDDEN_TABLES, PII_COLUMNS

SCHEMA_METADATA: dict[str, dict] = {
    "doudian_order": {
        "description": "Douyin shop orders with amount, pay time, status, goods name, and raw payload.",
        "key_columns": ["order_sn", "goods_name", "sale_num", "order_amount", "pay_time", "status"],
        "time_columns": ["pay_time", "scraped_at"],
        "pii_columns": ["order_sn"],
    },
    "doudian_goods": {
        "description": "Product snapshots with title, price, stock, clicks, conversion rate, tab, and status.",
        "key_columns": ["goods_id", "title", "price", "stock", "click_num", "convert_rate", "tab"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "doudian_comment": {
        "description": "Product comments with rating, content, user nickname, AI sentiment, and pain-point tags.",
        "key_columns": ["comment_id", "goods_id", "content", "rating", "user_nick", "sentiment"],
        "time_columns": ["created_at_src", "scraped_at"],
        "pii_columns": ["user_nick"],
    },
    "doudian_stock": {
        "description": "SKU and warehouse stock snapshots.",
        "key_columns": ["goods_id", "sku_id", "warehouse_id", "on_hand", "available", "locked"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "doudian_aftersale": {
        "description": "Aftersale/refund records with order link, reason, refund amount, status, and deadline.",
        "key_columns": ["aftersale_id", "order_sn", "type", "reason", "refund_amount", "status"],
        "time_columns": ["created_at_src", "deadline_at", "scraped_at"],
        "pii_columns": ["order_sn"],
    },
    "comment_tag_stat": {
        "description": "Aggregated negative-comment pain-point counts by shop or goods scope.",
        "key_columns": ["scope", "scope_id", "tag", "neg_count", "total_count"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "aftersale_counts": {
        "description": "Aftersale dashboard count dimensions from the latest scraped snapshot.",
        "key_columns": ["dim", "count"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "member_dashboard_agg": {
        "description": "Member dashboard aggregate KPIs from Douyin member analytics.",
        "key_columns": ["raw_json", "scraped_at"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "compass_core_data": {
        "description": "Compass search/core analytics KPI snapshots.",
        "key_columns": ["raw_json", "scraped_at"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
    "compass_core_trend": {
        "description": "Compass trend time series for search and shop metrics.",
        "key_columns": ["raw_json", "scraped_at"],
        "time_columns": ["scraped_at"],
        "pii_columns": [],
    },
}


def schema_summary() -> str:
    lines = ["Available business tables for readonly SQL:"]
    for name in sorted(ALLOWED_TABLES):
        meta = SCHEMA_METADATA.get(name, {})
        desc = meta.get("description", "Scraped business-data table.")
        time_cols = ", ".join(meta.get("time_columns", [])) or "scraped_at/raw_json"
        lines.append(f"- {name}: {desc} Time columns: {time_cols}.")
    lines.append(
        "Do not query secret/control tables. The merchant operator is authorized to inspect raw business and order fields returned by approved tools. Use describe_schema for detail."
    )
    return "\n".join(lines)


def describe_schema(table_name: str) -> dict:
    name = table_name.lower()
    if name in FORBIDDEN_TABLES or name.startswith("chat_") or name not in ALLOWED_TABLES:
        return {"ok": False, "error": "forbidden_table", "table": table_name}
    meta = SCHEMA_METADATA.get(name, {})
    return {
        "ok": True,
        "table": name,
        "description": meta.get("description", "Scraped business-data table."),
        "key_columns": meta.get("key_columns", []),
        "time_columns": meta.get("time_columns", ["scraped_at"]),
        "pii_columns": meta.get("pii_columns", [col for col in PII_COLUMNS if col in name]),
    }
