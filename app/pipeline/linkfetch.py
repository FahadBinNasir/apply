from __future__ import annotations
import ipaddress
import socket
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import httpx
from bs4 import BeautifulSoup

from contracts.protocols import LinkFetcher

BLOCKED_DOMAINS = ["linkedin.com", "lnkd.in", "www.linkedin.com"]


def _strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {
        k: v
        for k, v in query_params.items()
        if not k.startswith("utm_") and k not in ["fbclid", "gclid", "ref", "mc_eid"]
    }
    clean_query = urlencode(filtered, doseq=True)
    return urlunparse(parsed._replace(query=clean_query))


def _validate_ssrf(url: str) -> Tuple[bool, Optional[str]]:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False, f"Unsupported scheme: {parsed.scheme}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname"

        if hostname.lower() in ["localhost", "127.0.0.1", "::1"]:
            return False, "Localhost access blocked"

        # Resolve IP to check for private or link-local subnets
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
                    return False, f"SSRF blocked: Host resolves to private/loopback IP {ip_str}"
        except socket.gaierror:
            return False, f"Could not resolve hostname: {hostname}"

        return True, None
    except Exception as e:
        return False, f"URL parse error: {e}"


class ProductionLinkFetcher:
    """Safe web content extractor with strict SSRF defense."""

    def __init__(self, timeout: float = 10.0, max_bytes: int = 1_048_576):
        self.timeout = timeout
        self.max_bytes = max_bytes

    async def fetch_link(self, url: str) -> Tuple[bool, str, Optional[str]]:
        clean_url = _strip_tracking_params(url)
        parsed = urlparse(clean_url)

        # Check walled gardens
        if any(d in (parsed.hostname or "").lower() for d in BLOCKED_DOMAINS):
            return False, "", "LinkedIn link requires login wall / manual action"

        # SSRF Check
        is_safe, ssrf_err = _validate_ssrf(clean_url)
        if not is_safe:
            return False, "", f"SSRF Guard: {ssrf_err}"

        # Fetch with httpx
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as client:
                resp = await client.get(clean_url)

                # Re-validate target after redirect
                is_safe_target, target_err = _validate_ssrf(str(resp.url))
                if not is_safe_target:
                    return False, "", f"SSRF Redirect Guard: {target_err}"

                if resp.status_code >= 400:
                    return False, "", f"HTTP {resp.status_code} error from target server"

                html = resp.text[: self.max_bytes]

                # Extract text using BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()

                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = "\n".join(lines)

                if len(clean_text) < 50:
                    return False, "", "Page body contained insufficient text content"

                return True, clean_text[:8000], None
        except Exception as e:
            return False, "", f"Network/fetch failure: {e}"
