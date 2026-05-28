"""PII scrubbing for prompts sent to external LLM providers."""

import re

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ORDER_SN_RE = re.compile(r"(?<![A-Za-z\d])[A-Z]{0,5}\d{12,20}(?![A-Za-z\d])")
ADDRESS_RE = re.compile(
    r"[\u4e00-\u9fa5]{2,12}(?:省|市|自治区|区|县)"
    r"[\u4e00-\u9fa5]{0,20}(?:路|街|巷|道|大道|小区|园区)"
    r"[\u4e00-\u9fa5\d号弄室楼单元\-]{1,30}"
)


class Scrubber:
    def __init__(self) -> None:
        self._phones: dict[str, str] = {}
        self._orders: dict[str, str] = {}
        self._addresses: dict[str, str] = {}
        self._nicks: dict[str, str] = {}

    def _placeholder(self, store: dict[str, str], value: str, prefix: str) -> str:
        if value not in store:
            store[value] = f"<{prefix}_{len(store) + 1:03d}>"
        return store[value]

    def scrub(self, text: str, *, nicks: list[str] | None = None) -> str:
        for nick in sorted(nicks or [], key=len, reverse=True):
            if nick and nick in text:
                text = text.replace(nick, self._placeholder(self._nicks, nick, "NICK"))
        text = PHONE_RE.sub(lambda m: self._placeholder(self._phones, m.group(0), "PHONE"), text)
        text = ADDRESS_RE.sub(lambda m: self._placeholder(self._addresses, m.group(0), "ADDR"), text)
        text = ORDER_SN_RE.sub(lambda m: self._placeholder(self._orders, m.group(0), "ORDER"), text)
        return text

    @property
    def mapping(self) -> dict[str, dict[str, str]]:
        return {
            "phones": dict(self._phones),
            "orders": dict(self._orders),
            "addresses": dict(self._addresses),
            "nicks": dict(self._nicks),
        }
