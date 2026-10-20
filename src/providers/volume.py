"""Search Volume Provider Architecture and Epistemic Modesty Service.

Provides a clean provider interface for keyword search volume:
- Strict epistemic modesty: Never conflates YouTube video views or autocomplete suggestions with monthly searches
- Structured KeywordSearchVolume domain model
- UnconnectedSearchVolumeProvider: Truthful fallback displaying 'Volume unavailable'
- Ready for integration with verified third-party keyword volume providers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional


@dataclass
class KeywordSearchVolume:
    """Represents verified or transparently estimated monthly search volume."""

    keyword: str
    monthly_volume: Optional[int] = None
    volume_range: str = "Volume unavailable"
    status: str = "Unavailable"  # "Sourced", "Estimated", or "Unavailable"
    provider_name: str = "None (Unconnected)"
    target_country: str = "US"
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    explanation: str = (
        "YouTube does not publicly disclose monthly search counts. "
        "Metric is honestly marked 'Volume unavailable' rather than fabricated."
    )

    @property
    def display_metric(self) -> str:
        """Return clean human-readable volume string for UI display."""
        if self.monthly_volume is not None and self.status == "Sourced":
            return f"{self.monthly_volume:,} / mo"
        return self.volume_range


class BaseSearchVolumeProvider:
    """Abstract base class for search volume providers."""

    def is_connected(self) -> bool:
        """Return True if external search volume provider credentials are valid."""
        return False

    def get_keyword_volume(
        self, keyword: str, country: str = "US"
    ) -> KeywordSearchVolume:
        """Retrieve monthly search volume for a target keyword."""
        raise NotImplementedError


class UnconnectedSearchVolumeProvider(BaseSearchVolumeProvider):
    """Default local-first search volume provider.
    
    Guarantees zero fabricated metrics when third-party search volume APIs are unconfigured.
    """

    def __init__(self, provider_name: str = "Unconnected Local Provider") -> None:
        self.provider_name = provider_name

    def is_connected(self) -> bool:
        """Return False as provider is unconnected."""
        return False

    def get_keyword_volume(
        self, keyword: str, country: str = "US"
    ) -> KeywordSearchVolume:
        """Return truthful unavailable volume state."""
        clean_kw = keyword.strip()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return KeywordSearchVolume(
            keyword=clean_kw,
            monthly_volume=None,
            volume_range="Volume unavailable",
            status="Unavailable",
            provider_name=self.provider_name,
            target_country=country,
            retrieved_at=now_str,
            explanation=(
                f"No third-party search volume API configured for '{clean_kw}'. "
                f"YouTube autocomplete indicates active search interest, but exact monthly volume is not public."
            ),
        )


# Default volume provider instance
default_volume_provider = UnconnectedSearchVolumeProvider()
