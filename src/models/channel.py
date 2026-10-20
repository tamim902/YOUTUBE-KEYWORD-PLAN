"""Domain models for Four-Channel Portfolio and Profile Workspaces (Phase 22 Part 1)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChannelProfile:
    """Configurable channel profile for multi-channel YouTube portfolio."""

    id: Optional[int] = None
    channel_name: str = "Channel 1"
    channel_handle: str = ""
    channel_url: str = ""
    channel_niche: str = "General Tech"
    sub_niches: List[str] = field(default_factory=list)
    target_audience: str = "General Audience"
    target_country: str = "US"
    target_language: str = "en"
    content_format: str = "both"  # "long_form", "shorts", "both"
    affiliate_enabled: bool = True
    preferred_affiliate_markets: List[str] = field(default_factory=lambda: ["Amazon Associates"])
    preferred_publishing_frequency: str = "2 videos / week"
    existing_video_topics: List[str] = field(default_factory=list)
    excluded_topics: List[str] = field(default_factory=list)
    excluded_brands: List[str] = field(default_factory=list)
    excluded_products: List[str] = field(default_factory=list)
    excluded_keywords: List[str] = field(default_factory=list)
    channel_footer: str = ""
    seo_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "min_keyword_length": 3,
            "max_title_chars": 65,
            "default_tags": [],
            "brand_in_title": False,
            "auto_include_year": True,
        }
    )
    daily_research_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "date_window_days": 60,
            "request_budget": 20,
            "min_coverage": 2,
            "max_daily_ideas": 10,
            "generate_descriptions": True,
            "auto_title_count": 5,
        }
    )
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to serializable dictionary."""
        return asdict(self)

    @property
    def niche(self) -> str:
        """Alias for channel_niche."""
        return self.channel_niche

    @property
    def affiliate_marketing_enabled(self) -> bool:
        """Alias for affiliate_enabled."""
        return self.affiliate_enabled

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelProfile":
        """Reconstruct channel profile from dictionary safely."""
        valid_keys = {
            "id", "channel_name", "channel_handle", "channel_url", "channel_niche",
            "sub_niches", "target_audience", "target_country", "target_language",
            "content_format", "affiliate_enabled", "preferred_affiliate_markets",
            "preferred_publishing_frequency", "existing_video_topics", "excluded_topics",
            "excluded_brands", "excluded_products", "excluded_keywords", "channel_footer",
            "seo_settings", "daily_research_settings", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def validate_channel_url(self) -> Tuple[bool, str]:
        """Validate that channel URL uses supported public YouTube web patterns."""
        if not self.channel_url or not self.channel_url.strip():
            return True, "No URL configured (Optional)."
        url = self.channel_url.strip()
        pattern = r"^(https?:\/\/)?(www\.)?(youtube\.com\/(c\/|channel\/|user\/|@)[a-zA-Z0-9_\-\.]+)"
        if re.match(pattern, url, re.IGNORECASE):
            return True, "Valid public YouTube channel URL."
        return False, "Invalid format. Expected https://youtube.com/@handle or https://youtube.com/channel/..."

    def is_topic_excluded(self, text: str) -> bool:
        """Check if candidate keyword or product contains any excluded token."""
        excluded, _ = self.is_excluded(text)
        return excluded

    def is_excluded(self, text: str) -> Tuple[bool, str]:
        """Check if text contains any excluded token and return reason if matched."""
        if not text:
            return False, ""
        lower_text = text.lower()
        for t in self.excluded_topics:
            if t and t.lower() in lower_text:
                return True, f"Excluded topic: {t}"
        for b in self.excluded_brands:
            if b and b.lower() in lower_text:
                return True, f"Excluded brand: {b}"
        for p in self.excluded_products:
            if p and p.lower() in lower_text:
                return True, f"Excluded product: {p}"
        for k in self.excluded_keywords:
            if k and k.lower() in lower_text:
                return True, f"Excluded keyword: {k}"
        return False, ""



def get_default_four_channels() -> List[ChannelProfile]:
    """Generate 4 distinct realistic starter channel profiles for the four-channel workspace."""
    return [
        ChannelProfile(
            id=1,
            channel_name="TechGear Pulse",
            channel_handle="@TechGearPulse",
            channel_url="https://youtube.com/@TechGearPulse",
            channel_niche="Mechanical Keyboards & Desk Setup",
            sub_niches=["Custom Keyboards", "Linear Switches", "Keycaps", "Desk Mats", "Audio Interfaces"],
            target_audience="PC enthusiasts, software engineers, and desk setup aesthetic creators",
            target_country="US",
            target_language="en",
            content_format="both",
            affiliate_enabled=True,
            preferred_affiliate_markets=["Amazon Associates", "Drop", "Epomaker", "Keychron Affiliate"],
            preferred_publishing_frequency="2 videos / week",
            existing_video_topics=["Best Budget Keyboards 2026", "Lubing Switches Guide", "Keychron V1 Review"],
            excluded_topics=["Cheap membrane keyboards", "RGB office mice"],
            excluded_brands=["Generic Wholesale"],
            excluded_products=["Toy keyboards"],
            excluded_keywords=["free keyboard hack", "cracked software"],
            channel_footer="TechGear Pulse • Independent mechanical keyboard reviews and desk setup guides.\nLinks above may be affiliate links. Opinions are strictly our own.",
            seo_settings={
                "min_keyword_length": 3,
                "max_title_chars": 60,
                "default_tags": ["mechanical keyboard", "custom keyboard", "desk setup", "tech review"],
                "brand_in_title": False,
                "auto_include_year": True,
            },
            daily_research_settings={
                "date_window_days": 60,
                "request_budget": 20,
                "min_coverage": 2,
                "max_daily_ideas": 10,
                "generate_descriptions": True,
                "auto_title_count": 6,
            },
        ),
        ChannelProfile(
            id=2,
            channel_name="CodeCraft বাংলা",
            channel_handle="@CodeCraftBangla",
            channel_url="https://youtube.com/@CodeCraftBangla",
            channel_niche="Python, AI & Web Development",
            sub_niches=["Python Tutorials", "FastAPI", "Machine Learning", "Streamlit Apps", "Career in Tech"],
            target_audience="Bangla-speaking students, junior programmers, and aspiring software engineers",
            target_country="BD",
            target_language="bn",
            content_format="long_form",
            affiliate_enabled=True,
            preferred_affiliate_markets=["Udemy Affiliate", "Coursera", "Namecheap", "Hostinger"],
            preferred_publishing_frequency="3 videos / week",
            existing_video_topics=["Python পূর্ণাঙ্গ টিউটোরিয়াল", "FastAPI দিয়ে REST API", "Machine Learning শুরু"],
            excluded_topics=["Online gambling apps", "Typing jobs"],
            excluded_brands=["Spam hosting"],
            excluded_products=[],
            excluded_keywords=["earn money without skill", "free certificate hack"],
            channel_footer="CodeCraft বাংলা • বাংলায় আধুনিক প্রোগ্রামিং ও সফটওয়্যার ইঞ্জিনিয়ারিং শিখুন।\nভিডিওতে উল্লেখিত কোনো কোর্স লিঙ্ক থেকে সাবস্ক্রাইব করলে আমরা সামান্য কমিশন পেতে পারি।",
            seo_settings={
                "min_keyword_length": 2,
                "max_title_chars": 65,
                "default_tags": ["python tutorial bangla", "programming bangla", "learn coding", "ai bangla"],
                "brand_in_title": True,
                "auto_include_year": True,
            },
            daily_research_settings={
                "date_window_days": 60,
                "request_budget": 15,
                "min_coverage": 2,
                "max_daily_ideas": 8,
                "generate_descriptions": True,
                "auto_title_count": 5,
            },
        ),
        ChannelProfile(
            id=3,
            channel_name="HomeChef Artisan",
            channel_handle="@HomeChefArtisan",
            channel_url="https://youtube.com/@HomeChefArtisan",
            channel_niche="Kitchen Appliances & Espresso Equipment",
            sub_niches=["Espresso Machines", "Coffee Grinders", "Air Fryers", "Sous Vide", "Chef Knives"],
            target_audience="Home baristas, gourmet home cooks, and kitchen gadget shoppers",
            target_country="US",
            target_language="en",
            content_format="both",
            affiliate_enabled=True,
            preferred_affiliate_markets=["Amazon Associates", "Williams-Sonoma", "Seattle Coffee Gear", "Sur La Table"],
            preferred_publishing_frequency="1 video / week",
            existing_video_topics=["Breville Barista Touch Review", "Best Conical Burr Grinders", "Air Fryer vs Convection"],
            excluded_topics=["Disposable cookware", "Fast food hacks"],
            excluded_brands=["Generic Plasticware"],
            excluded_products=[],
            excluded_keywords=["microwave dinner", "cheap junk"],
            channel_footer="HomeChef Artisan • In-depth, honest tests of specialty coffee gear and culinary equipment.\nWe only recommend equipment we have empirically tested. Affiliate links help support this channel.",
            seo_settings={
                "min_keyword_length": 3,
                "max_title_chars": 60,
                "default_tags": ["espresso machine", "coffee gear", "kitchen review", "home chef"],
                "brand_in_title": False,
                "auto_include_year": True,
            },
            daily_research_settings={
                "date_window_days": 60,
                "request_budget": 20,
                "min_coverage": 2,
                "max_daily_ideas": 10,
                "generate_descriptions": True,
                "auto_title_count": 6,
            },
        ),
        ChannelProfile(
            id=4,
            channel_name="FitPulse Active",
            channel_handle="@FitPulseActive",
            channel_url="https://youtube.com/@FitPulseActive",
            channel_niche="Home Gym & Recovery Technology",
            sub_niches=["Massage Guns", "Smart Dumbbells", "Wearable Fitness Trackers", "Resistance Bands", "Cold Plunges"],
            target_audience="Home fitness practitioners, runners, and tech-driven wellness athletes",
            target_country="GB",
            target_language="en",
            content_format="both",
            affiliate_enabled=True,
            preferred_affiliate_markets=["Amazon Associates UK", "MyProtein", "Gymshark", "Rogue Fitness"],
            preferred_publishing_frequency="2 videos / week",
            existing_video_topics=["Theragun vs Hypervolt", "Best Adjustable Dumbbells UK", "Whoop 4.0 One Year Later"],
            excluded_topics=["Dangerous workout supplements", "Quick weight loss pills"],
            excluded_brands=["Black market supplements"],
            excluded_products=["Fad diet pills"],
            excluded_keywords=["lose 10kg in 3 days", "anabolic steroid"],
            channel_footer="FitPulse Active • Science-grounded fitness tech and home gym equipment reviews.\nConsult a physician before starting any training program. Affiliate links fund our testing laboratory.",
            seo_settings={
                "min_keyword_length": 3,
                "max_title_chars": 60,
                "default_tags": ["home gym", "fitness tech", "massage gun", "workout gear"],
                "brand_in_title": False,
                "auto_include_year": True,
            },
            daily_research_settings={
                "date_window_days": 60,
                "request_budget": 20,
                "min_coverage": 2,
                "max_daily_ideas": 10,
                "generate_descriptions": True,
                "auto_title_count": 6,
            },
        ),
    ]
