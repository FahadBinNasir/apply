from __future__ import annotations
from typing import Dict, Optional, Tuple
from contracts.protocols import LinkFetcher


class FakeLinkFetcher:
    def __init__(self, canned_pages: Optional[Dict[str, str]] = None):
        self.canned_pages: Dict[str, str] = canned_pages or {}

    def set_page(self, url: str, content: str) -> None:
        self.canned_pages[url] = content

    async def fetch_link(self, url: str) -> Tuple[bool, str, Optional[str]]:
        # SSRF checks
        if "127.0.0.1" in url or "localhost" in url or "192.168." in url or "10." in url:
            return False, "", "SSRF: Blocked local/private IP address"

        # LinkedIn login wall
        if "linkedin.com" in url or "lnkd.in" in url:
            return False, "", "LinkedIn link requires login wall / manual action"

        if url in self.canned_pages:
            return True, self.canned_pages[url], None

        return True, f"Mocked webpage content for {url}. Looking for talented software engineers in Karachi.", None
