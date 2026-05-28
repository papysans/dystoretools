"""Discover and validate scrape-target YAML specs at startup."""
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from dystore.core.logging import get_logger
from dystore.scraper.schema import ScrapeSpec

log = get_logger(__name__)

SPECS_DIR = Path(__file__).parent / "specs"


class SpecLoadError(RuntimeError):
    pass


@lru_cache
def load_all() -> dict[str, ScrapeSpec]:
    specs: dict[str, ScrapeSpec] = {}
    errors: list[str] = []
    for path in sorted(SPECS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            spec = ScrapeSpec.model_validate(data)
        except (yaml.YAMLError, ValidationError) as e:
            errors.append(f"{path.name}: {e}")
            continue
        if spec.target in specs:
            errors.append(f"{path.name}: duplicate target '{spec.target}'")
            continue
        specs[spec.target] = spec
    if errors:
        raise SpecLoadError("\n".join(errors))
    log.info("scraper.specs_loaded", count=len(specs), targets=list(specs.keys()))
    return specs


def get(target: str) -> ScrapeSpec:
    specs = load_all()
    if target not in specs:
        raise KeyError(f"unknown target: {target}")
    return specs[target]
