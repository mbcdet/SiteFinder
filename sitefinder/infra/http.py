from __future__ import annotations

import httpx

USER_AGENT = "SiteFinder/0.1 (lead-generation MVP)"


def build_client(timeout: float) -> httpx.Client:
    """Shared httpx client with a polite User-Agent and a sane timeout."""
    return httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})
