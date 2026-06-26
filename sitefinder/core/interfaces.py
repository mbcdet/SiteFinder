from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from sitefinder.core.enums import SourceName
from sitefinder.core.models import (
    Business,
    DiscoveryQuery,
    QueryCriteria,
    RunReport,
    WebPresence,
)


class DataSource(ABC):
    """Discovers businesses for a query, returning normalized Business objects.
    Each implementation owns its access method (API or browser automation)."""

    name: SourceName

    @abstractmethod
    def discover(self, query: DiscoveryQuery) -> Iterable[Business]: ...


class Enricher(ABC):
    """Optionally augments a Business (rating, reviews, website, provider ids)."""

    name: SourceName

    @abstractmethod
    def supports(self, business: Business) -> bool: ...

    @abstractmethod
    def enrich(self, business: Business) -> Business: ...


class WebsiteChecker(ABC):
    """Classifies web presence (Phase 1); audits quality later (Phase 2)."""

    @abstractmethod
    def classify(self, business: Business) -> WebPresence: ...


class Repository(ABC):
    """Persistence boundary. Hides the storage engine from the rest of the app."""

    @abstractmethod
    def upsert(self, business: Business) -> None: ...

    @abstractmethod
    def get(self, business_id: str) -> Business | None: ...

    @abstractmethod
    def find(self, criteria: QueryCriteria) -> list[Business]: ...

    @abstractmethod
    def find_match(self, business: Business) -> Business | None: ...

    @abstractmethod
    def soft_delete(self, business_id: str) -> None: ...

    @abstractmethod
    def save_report(self, report: RunReport) -> None: ...


class Exporter(ABC):
    """Renders businesses to an output format (CSV now)."""

    @abstractmethod
    def export(self, businesses: Iterable[Business], destination: Path) -> Path: ...


class Reporter(ABC):
    """Renders a RunReport (console + file). Pure presentation; computes no metrics."""

    @abstractmethod
    def render(self, report: RunReport, destination: Path | None = None) -> str: ...
