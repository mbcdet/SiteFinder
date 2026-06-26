"""Lightweight, dependency-free HTML heuristics for the audit checkers.

Regex-based on purpose: the checks are heuristics, not a DOM parse, so we avoid pulling in a
parser dependency. Good enough to flag "is there a title / viewport / alt text / contact link".
"""

from __future__ import annotations

import re

_I = re.IGNORECASE
_IS = re.IGNORECASE | re.DOTALL


def title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, _IS)
    return m.group(1).strip() if m else ""


def has_viewport(html: str) -> bool:
    return bool(re.search(r"<meta[^>]+name=[\"']viewport[\"']", html, _I))


def has_meta_description(html: str) -> bool:
    return bool(
        re.search(r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"'][^\"']{1,}", html, _I)
    )


def has_h1(html: str) -> bool:
    return bool(re.search(r"<h1[\s>]", html, _I))


def lang(html: str) -> str:
    m = re.search(r"<html[^>]*\blang=[\"']([^\"']+)", html, _I)
    return m.group(1) if m else ""


def img_alt_ratio(html: str) -> float:
    """Fraction of <img> tags that have a non-empty alt attribute. 1.0 when there are no images."""
    imgs = re.findall(r"<img\b[^>]*>", html, _I)
    if not imgs:
        return 1.0
    with_alt = sum(1 for tag in imgs if re.search(r"\balt=[\"'][^\"']", tag, _I))
    return with_alt / len(imgs)


def has_tel_or_mailto(html: str) -> bool:
    return bool(re.search(r"href=[\"'](tel:|mailto:)", html, _I))


def contains_any(html: str, needles: tuple[str, ...]) -> bool:
    low = html.lower()
    return any(n in low for n in needles)
