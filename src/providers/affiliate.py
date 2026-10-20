"""Affiliate and merchant metadata providers for Phase 14.

Follows strict non-fabrication rules:
- Unverified prices, rates, and commissions are marked "Needs verification"
- No fake store links, conversion estimates, or earnings predictions
- Local-first and extensible
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from src.models.product_planner import AffiliateProductData

logger = logging.getLogger(__name__)


class BaseAffiliateProvider(ABC):
    """Abstract base provider for product affiliate and merchant lookup."""

    @abstractmethod
    def lookup_product(
        self, product_name: str, brand: str = "", model: str = ""
    ) -> Optional[AffiliateProductData]:
        """Lookup merchant and affiliate info for a product."""
        pass


class ManualAffiliateProvider(BaseAffiliateProvider):
    """Handles user-entered or manually verified affiliate data."""

    def lookup_product(
        self, product_name: str, brand: str = "", model: str = ""
    ) -> Optional[AffiliateProductData]:
        # Manual provider does not automatically fetch external data without input
        return None

    @staticmethod
    def create_record(
        product_name: str,
        brand: str = "",
        model: str = "",
        merchant: str = "",
        product_page_url: str = "",
        price: Optional[float] = None,
        currency: str = "USD",
        affiliate_program: str = "",
        commission_info: Optional[str] = None,
        availability: str = "Unknown",
        affiliate_link: str = "",
        is_verified_merchant: bool = False,
        notes: str = "",
    ) -> AffiliateProductData:
        """Create a validated affiliate data record with non-fabrication guarantees."""
        comm = (
            commission_info.strip()
            if commission_info and commission_info.strip()
            else "Needs verification"
        )
        url = product_page_url.strip() if product_page_url else ""
        aff_url = affiliate_link.strip() if affiliate_link else ""
        merch = merchant.strip() if merchant else "Needs verification"

        return AffiliateProductData(
            product_name=product_name.strip(),
            brand=brand.strip(),
            model=model.strip(),
            product_page_url=url,
            merchant=merch,
            price=price,
            currency=currency.upper() if currency else "USD",
            affiliate_program=affiliate_program.strip() if affiliate_program else "Needs verification",
            commission_info=comm,
            availability=availability if availability in ["In Stock", "Pre-Order", "Backordered", "Out of Stock", "Unknown"] else "Unknown",
            affiliate_link=aff_url,
            is_verified_merchant=bool(is_verified_merchant),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            notes=notes.strip() if notes else "",
        )


class CuratedCatalogAffiliateProvider(BaseAffiliateProvider):
    """Catalog provider that checks a known verified local dictionary or catalog."""

    def __init__(self, catalog: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self.catalog = catalog or {}

    def add_catalog_entry(self, key: str, data: Dict[str, Any]) -> None:
        """Add a verified product affiliate entry."""
        self.catalog[key.lower().strip()] = data

    def lookup_product(
        self, product_name: str, brand: str = "", model: str = ""
    ) -> Optional[AffiliateProductData]:
        clean_name = product_name.lower().strip()
        clean_model = model.lower().strip()

        # Check by product name or model
        entry = self.catalog.get(clean_name) or (
            self.catalog.get(clean_model) if clean_model else None
        )
        if not entry:
            # Partial match check
            for k, v in self.catalog.items():
                if k in clean_name or (clean_model and k in clean_model):
                    entry = v
                    break

        if not entry:
            return None

        return AffiliateProductData(
            product_name=entry.get("product_name", product_name),
            brand=entry.get("brand", brand),
            model=entry.get("model", model),
            product_page_url=entry.get("product_page_url", ""),
            merchant=entry.get("merchant", "Needs verification"),
            price=entry.get("price"),
            currency=entry.get("currency", "USD"),
            affiliate_program=entry.get("affiliate_program", "Needs verification"),
            commission_info=entry.get("commission_info", "Needs verification"),
            availability=entry.get("availability", "Unknown"),
            affiliate_link=entry.get("affiliate_link", ""),
            is_verified_merchant=entry.get("is_verified_merchant", False),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            notes=entry.get("notes", "Matched from verified catalog"),
        )


class MockAffiliateProvider(BaseAffiliateProvider):
    """Deterministic mock provider for automated tests."""

    def __init__(self) -> None:
        self._test_database = {
            "sony wf-1000xm5": {
                "product_name": "Sony WF-1000XM5",
                "brand": "Sony",
                "model": "WF-1000XM5",
                "merchant": "Amazon",
                "product_page_url": "https://www.sony.com/electronics/truly-wireless/wf-1000xm5",
                "price": 299.99,
                "currency": "USD",
                "affiliate_program": "Amazon Associates",
                "commission_info": "1-3% Fixed Rate (Electronics)",
                "availability": "In Stock",
                "affiliate_link": "https://amzn.to/example-wf-1000xm5",
                "is_verified_merchant": True,
                "notes": "Official flagship wireless earbuds",
            },
            "bose quietcomfort ultra": {
                "product_name": "Bose QuietComfort Ultra",
                "brand": "Bose",
                "model": "QC Ultra",
                "merchant": "Best Buy",
                "product_page_url": "https://www.bose.com/p/earbuds/quietcomfort-ultra-earbuds",
                "price": 299.00,
                "currency": "USD",
                "affiliate_program": "Best Buy Affiliate",
                "commission_info": "0.5% (Consumer Electronics)",
                "availability": "In Stock",
                "affiliate_link": "",
                "is_verified_merchant": True,
                "notes": "Verified merchant catalog entry",
            },
        }

    def lookup_product(
        self, product_name: str, brand: str = "", model: str = ""
    ) -> Optional[AffiliateProductData]:
        clean_key = product_name.lower().strip()
        for key, entry in self._test_database.items():
            if key in clean_key or clean_key in key:
                return AffiliateProductData(
                    product_name=entry["product_name"],
                    brand=entry["brand"],
                    model=entry["model"],
                    product_page_url=entry["product_page_url"],
                    merchant=entry["merchant"],
                    price=entry["price"],
                    currency=entry["currency"],
                    affiliate_program=entry["affiliate_program"],
                    commission_info=entry["commission_info"],
                    availability=entry["availability"],
                    affiliate_link=entry["affiliate_link"],
                    is_verified_merchant=entry["is_verified_merchant"],
                    notes=entry["notes"],
                )
        return None
