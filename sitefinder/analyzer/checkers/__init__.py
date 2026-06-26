from sitefinder.analyzer.checkers.accessibility import AccessibilityChecker
from sitefinder.analyzer.checkers.booking import BookingChecker
from sitefinder.analyzer.checkers.broken_links import BrokenLinkChecker
from sitefinder.analyzer.checkers.contact import ContactInfoChecker
from sitefinder.analyzer.checkers.mobile import MobileFriendlinessChecker
from sitefinder.analyzer.checkers.performance import PerformanceChecker
from sitefinder.analyzer.checkers.seo import SeoChecker
from sitefinder.analyzer.checkers.ssl import SslChecker

__all__ = [
    "AccessibilityChecker",
    "BookingChecker",
    "BrokenLinkChecker",
    "ContactInfoChecker",
    "MobileFriendlinessChecker",
    "PerformanceChecker",
    "SeoChecker",
    "SslChecker",
]


def default_checkers() -> list:
    """The standard audit checker set, ordered by typical importance."""
    return [
        SslChecker(),
        MobileFriendlinessChecker(),
        PerformanceChecker(),
        SeoChecker(),
        ContactInfoChecker(),
        BrokenLinkChecker(),
        AccessibilityChecker(),
        BookingChecker(),
    ]
