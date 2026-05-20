import httpx

from dystore.llm.gateway import _estimate_tokens, _is_retryable
from dystore.llm.pii_scrub import Scrubber


def test_estimate_tokens_grows_with_length() -> None:
    short = _estimate_tokens("hi")
    long = _estimate_tokens("x" * 9000)
    assert short < long
    assert long >= 3000


def test_is_retryable_429() -> None:
    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(429, request=req)
    err = httpx.HTTPStatusError("429", request=req, response=resp)
    assert _is_retryable(err)


def test_is_retryable_500() -> None:
    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(503, request=req)
    err = httpx.HTTPStatusError("503", request=req, response=resp)
    assert _is_retryable(err)


def test_is_not_retryable_400() -> None:
    req = httpx.Request("POST", "https://x")
    resp = httpx.Response(400, request=req)
    err = httpx.HTTPStatusError("400", request=req, response=resp)
    assert not _is_retryable(err)


def test_pii_scrub_phone() -> None:
    scrubber = Scrubber()
    out = scrubber.scrub("我的手机13900000001收不到验证码")
    assert "13900000001" not in out
    assert "<PHONE_001>" in out


def test_pii_scrub_phone_stable_mapping() -> None:
    scrubber = Scrubber()
    out1 = scrubber.scrub("13900000001 first")
    out2 = scrubber.scrub("13900000001 second")
    assert "<PHONE_001>" in out1 and "<PHONE_001>" in out2


def test_pii_scrub_address() -> None:
    scrubber = Scrubber()
    out = scrubber.scrub("收货地址: 上海市浦东新区张江路999号")
    assert "张江路999号" not in out
    assert "<ADDR_001>" in out


def test_pii_scrub_nick() -> None:
    scrubber = Scrubber()
    out = scrubber.scrub("用户小明留言：东西不错", nicks=["小明"])
    assert "小明" not in out
    assert "<NICK_001>" in out


def test_pii_scrub_no_pii_unchanged() -> None:
    scrubber = Scrubber()
    assert scrubber.scrub("一切正常没有敏感信息") == "一切正常没有敏感信息"
