"""Pydantic schema for declarative scrape-target YAML specs."""
from typing import Any, Literal

from pydantic import BaseModel, Field


Subsystem = Literal["merchant", "public", "maintenance"]
HttpMethod = Literal["GET", "POST", "PUT", "DELETE"]


class NavConfig(BaseModel):
    url: str
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = "networkidle"
    settle_ms: int = 2500


class ScheduleConfig(BaseModel):
    cron: str   # APScheduler cron expression (5 fields: min hour day month dow)


class InterceptConfig(BaseModel):
    url_contains: str
    method: HttpMethod = "GET"


class ExtractConfig(BaseModel):
    jsonpath: str
    fields: dict[str, str] = Field(default_factory=dict)   # column_name -> jsonpath
    # Literal values merged into every emitted row — for columns the API doesn't carry
    # but the table requires (e.g. metric='new_order_amt' when payload has only 'y.new_order_amt').
    static_fields: dict[str, Any] = Field(default_factory=dict)
    transforms: dict[str, str] = Field(default_factory=dict)
    # When True, treat the jsonpath result as a flat {key: value} object and emit one row
    # per (key, value) pair. `fields` is ignored in this mode.
    iterate_object: bool = False
    iterate_key_field: str = "dim"
    iterate_value_field: str = "count"


class SinkConfig(BaseModel):
    table: str
    upsert_key: str | None = None
    store_raw: bool = True
    # When True, ignore extract.jsonpath/fields and emit ONE row per captured payload
    # containing only raw_json + scraped_at. For tables that hold deeply-nested shapes
    # the frontend can parse on read.
    raw_only: bool = False


class PreAction(BaseModel):
    action: Literal["click", "fill", "select", "wait_for", "scroll"]
    selector: str | None = None
    value: str | int | None = None
    timeout_ms: int = 5_000


class ScrapeSpec(BaseModel):
    target: str = Field(..., description="Unique identifier; matches sink table or extends it")
    subsystem: Subsystem = "merchant"
    nav: NavConfig
    schedule: ScheduleConfig
    intercept: InterceptConfig
    extract: ExtractConfig
    sink: SinkConfig
    pre_actions: list[PreAction] = Field(default_factory=list)
    # When True, the scrape uses the page-side fetch evaluator rather than passive interception.
    # Useful for endpoints not auto-triggered by page load.
    fetch_eval: bool = False
