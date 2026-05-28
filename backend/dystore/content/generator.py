"""Content generator: load Jinja template + render prompt + call LLM."""
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from sqlalchemy import desc, select

from dystore.core.logging import get_logger
from dystore.db.models import DoudianComment, DoudianGoods  # noqa: F401  DoudianComment used in pain_point_cluster branch
from dystore.db.session import SessionLocal
from dystore.llm.gateway import complete
from dystore.llm.pii_scrub import Scrubber

log = get_logger(__name__)

ContentKind = Literal[
    "title", "detail", "livestream_script", "short_video_script",
    "comment_reply", "selection_advice", "pain_point_cluster",
]
TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(disabled_extensions=("j2",)),
    keep_trailing_newline=True,
)


class TemplateMissing(RuntimeError):
    pass


async def _build_recent_comments_summary(goods_id: str, *, n: int = 10) -> tuple[str, list[str]]:
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(DoudianComment)
                .where(DoudianComment.goods_id == goods_id)
                .order_by(desc(DoudianComment.id))
                .limit(n)
            )
        ).scalars().all()
    nicks = [r.user_nick for r in rows if r.user_nick]
    scrub = Scrubber()
    lines = []
    for r in rows:
        scrubbed = scrub.scrub(r.content or "", nicks=nicks)
        lines.append(f"- [{r.rating or '?'}星] {scrubbed[:120]}")
    return ("\n".join(lines), [r.user_nick for r in rows if r.user_nick])


async def generate(
    kind: ContentKind,
    goods_id: str,
    *,
    extra_context: str = "",
    comment_payload: dict | None = None,
) -> dict:
    """Render a template + dispatch to LLM.

    For kinds 'comment_reply' / 'pain_point_cluster' / 'selection_advice' the
    template context differs from the legacy goods-only flow.
    """
    template_name = f"{kind}.j2"
    try:
        tpl = _env.get_template(template_name)
    except TemplateNotFound as e:
        raise TemplateMissing(template_name) from e

    async with SessionLocal() as s:
        goods = (
            await s.execute(select(DoudianGoods).where(DoudianGoods.goods_id == goods_id))
        ).scalar_one_or_none()
    if goods is None:
        raise LookupError(f"unknown goods_id: {goods_id}")

    goods_ctx = {"title": goods.title, "price": goods.price, "category_id": goods.category_id}

    if kind == "comment_reply":
        if not comment_payload:
            raise ValueError("comment_reply requires comment_payload={rating, content}")
        prompt = tpl.render(goods=goods_ctx, comment=comment_payload, extra_context=extra_context)
    elif kind == "pain_point_cluster":
        # Pull recent negative (1-3 star) comments only
        async with SessionLocal() as s:
            rows = (
                await s.execute(
                    select(DoudianComment)
                    .where(DoudianComment.goods_id == goods_id)
                    .where(DoudianComment.rating <= 3)
                    .order_by(desc(DoudianComment.id))
                    .limit(20)
                )
            ).scalars().all()
        scrub = Scrubber()
        nicks = [r.user_nick for r in rows if r.user_nick]
        lines = [f"- [{r.rating or '?'}星] {scrub.scrub(r.content or '', nicks=nicks)[:200]}" for r in rows]
        prompt = tpl.render(
            goods=goods_ctx,
            comment_count=len(rows),
            comments_text="\n".join(lines) or "(暂无差评)",
            extra_context=extra_context,
        )
    elif kind == "selection_advice":
        # Provide structured summaries — frontend passes pre-built strings via extra_context
        # or we build them from the local DB.
        prompt = tpl.render(
            goods_summary=extra_context or f"商品：{goods.title}",
            aftersale_summary="见 dashboard",
            audience_summary="见 dashboard",
            peer_summary="见 dashboard",
            extra_context="",
        )
    else:
        summary, _ = await _build_recent_comments_summary(goods_id)
        prompt = tpl.render(
            goods=goods_ctx,
            recent_comments_summary=summary,
            extra_context=extra_context,
        )

    # Longer scripts (3-tier short video, livestream) need more headroom.
    max_tokens = 4096 if kind in ("short_video_script", "livestream_script") else 2048
    result = await complete(prompt, kind=kind, max_tokens=max_tokens)
    log.info("content.generated", kind=kind, goods_id=goods_id, tokens_in=result["tokens_in"], tokens_out=result["tokens_out"])
    return result
