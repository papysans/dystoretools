import pytest

from dystore.sqlsandbox.executor import mask_rows, validate_and_normalize_sql
from dystore.sqlsandbox.schema import describe_schema, schema_summary


def test_valid_select_adds_limit() -> None:
    sql, tables = validate_and_normalize_sql("select goods_id,title from doudian_goods", max_rows=20)
    assert "LIMIT 20" in sql.upper()
    assert tables == ["doudian_goods"]


def test_rejects_dml() -> None:
    with pytest.raises(ValueError, match="only_select_allowed"):
        validate_and_normalize_sql("delete from doudian_order")


def test_rejects_multiple_statements() -> None:
    with pytest.raises(ValueError, match="multiple_statements"):
        validate_and_normalize_sql("select * from doudian_goods; drop table doudian_goods")


def test_rejects_forbidden_table() -> None:
    with pytest.raises(ValueError, match="forbidden_table"):
        validate_and_normalize_sql("select * from llm_provider")


def test_reduces_large_limit() -> None:
    sql, _ = validate_and_normalize_sql("select * from doudian_comment limit 100000", max_rows=50)
    assert "LIMIT 50" in sql.upper()


def test_masks_pii_rows() -> None:
    rows = [{"receiver_phone": "13900000001", "content": "地址 上海市浦东新区张江路999号"}]
    masked = mask_rows(rows)
    assert "13900000001" not in str(masked)
    assert "张江路999号" not in str(masked)


def test_schema_summary_excludes_secret_tables() -> None:
    summary = schema_summary()
    assert "doudian_order" in summary
    assert "llm_provider" not in summary


def test_describe_schema_forbidden() -> None:
    assert describe_schema("llm_provider")["ok"] is False
    assert describe_schema("doudian_comment")["ok"] is True
