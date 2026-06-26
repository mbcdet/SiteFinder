from __future__ import annotations

import time
from typing import Any, Protocol

from sitefinder.analyzer.models import SiteSnapshot
from sitefinder.infra import http
from sitefinder.infra.logging import get_logger

log = get_logger(__name__)


class _HttpClient(Protocol):
    def get(self, url: str) -> Any: ...


def fetch_snapshot(
    url: str, timeout: float = 15.0, client: _HttpClient | None = None
) -> SiteSnapshot:
    """Fetch a URL once into a SiteSnapshot. Network failures are captured, never raised,
    so the audit degrades gracefully (an unreachable site is itself a strong lead signal)."""
    target = url if "://" in url else f"https://{url}"
    owns_client = client is None
    active = client or http.build_client(timeout, follow_redirects=True)
    try:
        start = time.monotonic()
        resp = active.get(target)
        elapsed = (time.monotonic() - start) * 1000
        final_url = str(resp.url)
        return SiteSnapshot(
            requested_url=url,
            final_url=final_url,
            reachable=True,
            status_code=resp.status_code,
            is_https=final_url.lower().startswith("https"),
            elapsed_ms=round(elapsed, 1),
            html=resp.text,
            headers={k.lower(): v for k, v in resp.headers.items()},
        )
    except Exception as exc:  # noqa: BLE001 - any network error -> unreachable snapshot
        log.info("Audit fetch failed for %s: %s", url, exc)
        return SiteSnapshot(requested_url=url, reachable=False, error=str(exc))
    finally:
        if owns_client:
            active.close()
