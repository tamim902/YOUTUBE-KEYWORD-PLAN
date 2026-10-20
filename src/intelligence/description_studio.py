"""YouTube SEO Description Studio & 8-Part Description Builder (Phase 22 Part 5).

Provides complete 8-part YouTube description generation:
- Section A: First 2-3 lines (Search hook & core promise before 'Show More')
- Section B: Video Summary (1-2 contextual paragraphs)
- Section C: Structured Timestamps / Chapters
- Section D: Links & Resources (Products mentioned)
- Section E: Mandatory FTC Affiliate Disclosure (enforced when affiliate links present)
- Section F: Channel Social & Subscribe Links
- Section G: Channel Bio & Policy Disclaimer
- Section H: 3-5 Relevant SEO Hashtags

Includes:
- Strict character counter (<=5000 characters)
- FTC affiliate disclosure detection
- Anti-keyword stuffing detection
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.models.channel import ChannelProfile
from src.models.seo import VideoDescription
from src.storage.database import DatabaseManager, db_manager


STANDARD_FTC_DISCLOSURE = (
    "DISCLOSURE: Some links in this description are affiliate links. If you make a purchase "
    "through them, this channel may earn a small commission at no additional cost to you. "
    "We only recommend products and gear we genuinely research or use. Thank you for supporting the channel!"
)


class DescriptionStudio:
    """Assembles, checks, and persists 8-part YouTube video descriptions."""

    def __init__(self, database: Optional[DatabaseManager] = None) -> None:
        self.db = database or db_manager

    def build_description(
        self,
        topic: str,
        primary_keyword: str,
        channel: ChannelProfile,
        custom_hook: Optional[str] = None,
        custom_summary: Optional[str] = None,
        affiliate_links: Optional[List[Dict[str, str]]] = None,
        timestamps: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        include_ftc_disclosure: Optional[bool] = None,
    ) -> VideoDescription:
        """Assemble a complete 8-part YouTube video description adhering to best SEO and FTC practices."""
        kw_clean = primary_keyword.strip()
        topic_clean = topic.strip()

        # Section A: Hook & Core Promise (First 2-3 lines before Show More)
        if custom_hook and custom_hook.strip():
            hook = custom_hook.strip()
        else:
            hook = (
                f"Looking for the best guide on {kw_clean}? In this video, we break down everything you need to know "
                f"about {topic_clean}, including practical tips, pros & cons, and key takeaways."
            )

        # Section B: Detailed Video Summary
        if custom_summary and custom_summary.strip():
            summary = custom_summary.strip()
        else:
            summary = (
                f"Whether you are just getting started or looking to upgrade your approach, {topic_clean} can make "
                f"a significant difference. We explore the essential factors, compare the top options, and give you "
                f"an honest, unbiased perspective so you can make the right decision for your setup."
            )

        # Section C: Timestamps / Chapters
        if timestamps and len(timestamps) > 0:
            chapters = "\n".join(timestamps)
        else:
            chapters = (
                "TIMESTAMPS:\n"
                "0:00 - Introduction & Overview\n"
                "1:15 - Key Concepts & What to Know\n"
                "3:40 - In-depth Breakdown & Hands-on Testing\n"
                "6:50 - Pros, Cons & Tradeoffs\n"
                "9:30 - Final Verdict & Recommendations"
            )

        # Section D: Links & Resources
        links_block = ""
        has_affiliate = False
        if affiliate_links and len(affiliate_links) > 0:
            has_affiliate = True
            lines = ["RESOURCES & PRODUCTS MENTIONED:"]
            for item in affiliate_links:
                label = item.get("label", "Product")
                url = item.get("url", "https://")
                lines.append(f"• {label}: {url}")
            links_block = "\n".join(lines)
        elif channel.affiliate_enabled:
            has_affiliate = True
            links_block = (
                "RESOURCES & PRODUCTS MENTIONED:\n"
                f"• Check current pricing & specs: [Add Your Product Link Here]\n"
                f"• Recommended gear & tools: [Add Your Tool Link Here]"
            )
        else:
            links_block = (
                "RESOURCES MENTIONED:\n"
                "• Official Documentation & Guides: [Link Here]"
            )

        # Section E: FTC Disclosure
        if include_ftc_disclosure is not None:
            use_disclosure = include_ftc_disclosure
        else:
            use_disclosure = has_affiliate or channel.affiliate_enabled

        ftc_block = STANDARD_FTC_DISCLOSURE if use_disclosure else ""

        # Section F: Channel Social & Subscribe
        social_block = (
            f"CONNECT WITH {channel.channel_name.upper()}:\n"
            f"🔔 Subscribe for more videos: {channel.channel_url if channel.channel_url else 'https://youtube.com/@channel'}\n"
            "💬 Drop a comment below if you have any questions!"
        )

        # Section G: Channel Bio / Disclaimer & Footer
        footer_block = channel.channel_footer.strip() if channel.channel_footer else (
            f"ABOUT {channel.channel_name.upper()}:\n"
            f"Welcome to {channel.channel_name}! We provide in-depth videos focused on {channel.channel_niche}. "
            "Our goal is to deliver honest, research-backed insights to help our viewers succeed."
        )

        # Section H: Hashtags (3-5 relevant hashtags)
        if hashtags and len(hashtags) > 0:
            tags_list = hashtags[:5]
        else:
            tag1 = re.sub(r"[^\w]", "", kw_clean)
            tag2 = re.sub(r"[^\w]", "", channel.channel_niche)
            tag3 = "YouTubeSEO"
            tag4 = "Review" if "review" in kw_clean.lower() else "Tutorial"
            tags_list = [f"#{t}" for t in [tag1, tag2, tag3, tag4] if t]

        hashtags_block = " ".join(tags_list)

        # Structured chapters list
        structured_chapters = [
            {"timestamp": "0:00", "label": "Introduction & Overview"},
            {"timestamp": "1:15", "label": f"Why {kw_clean} Matters"},
            {"timestamp": "3:40", "label": "Hands-on Breakdown & Deep Dive"},
            {"timestamp": "6:50", "label": "Pros, Cons & Tradeoffs"},
            {"timestamp": "9:30", "label": "Final Verdict & Recommendations"},
        ]

        # Structured affiliate links
        structured_affiliate: List[Dict[str, str]] = []
        if affiliate_links:
            structured_affiliate = affiliate_links
        elif channel.affiliate_enabled:
            structured_affiliate = [
                {"label": f"Recommended {kw_clean} Gear", "url": "https://amzn.to/example-link", "merchant": "Amazon Associates"}
            ]

        # Call to action & Hashtags
        cta_text = (
            f"🔔 Subscribe to {channel.channel_name} for more videos: {channel.channel_url if channel.channel_url else 'https://youtube.com/@channel'}\n"
            f"💬 Have questions about {kw_clean}? Drop a comment below!"
        )
        if hashtags_block:
            cta_text += f"\n\n{hashtags_block}"

        # Create description model
        desc = VideoDescription(
            channel_id=channel.id or 1,
            channel_name=channel.channel_name,
            topic=topic_clean,
            primary_keyword=kw_clean,
            opening_hook=hook,
            viewer_value=summary,
            chapters=structured_chapters,
            affiliate_links=structured_affiliate,
            affiliate_disclosure=ftc_block,
            calls_to_action=cta_text,
            channel_footer=footer_block,
            has_affiliate_links=bool(structured_affiliate),
            has_affiliate_disclosure=use_disclosure and bool(ftc_block),
        )

        desc.assemble_full_text()
        return desc

    def audit_description(self, desc: VideoDescription) -> Tuple[bool, List[str], List[str]]:
        """Audit description for FTC compliance, character limit, and keyword stuffing.
        
        Returns:
            (is_compliant, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Length check
        if desc.character_count > 5000:
            errors.append(f"Description exceeds YouTube's 5,000 character limit (currently {desc.character_count:,} characters).")
        elif desc.character_count > 4500:
            warnings.append(f"Description is near the 5,000 character limit ({desc.character_count:,}/5,000).")

        # 2. FTC Compliance check
        if desc.has_affiliate_links and not desc.has_affiliate_disclosure:
            errors.append("FTC Affiliate Disclosure is REQUIRED because affiliate links are included.")
        elif desc.has_affiliate_links and "affiliate" not in desc.full_text.lower():
            warnings.append("Affiliate links detected but standard 'affiliate' keyword not found in disclosure text.")

        # 3. Keyword stuffing check
        kw_lower = desc.primary_keyword.lower()
        full_lower = desc.full_text.lower()
        if kw_lower and len(kw_lower) > 2:
            occurrences = len(re.findall(re.escape(kw_lower), full_lower))
            total_words = len(re.findall(r"\b\w+\b", full_lower))
            if occurrences > 8:
                warnings.append(f"Primary keyword appears {occurrences} times. Consider reducing to avoid YouTube algorithmic spam penalties.")
            elif total_words > 0 and (occurrences / total_words) > 0.04:
                warnings.append(f"Keyword density is unusually high ({round(occurrences/total_words*100, 1)}%). Ensure natural phrasing.")

        # 4. Hashtag check
        tags = re.findall(r"#\w+", desc.full_text)
        if len(tags) > 15:
            errors.append(f"Too many hashtags ({len(tags)}). YouTube ignores all hashtags if more than 15 are used.")
        elif len(tags) > 5:
            warnings.append(f"{len(tags)} hashtags found. YouTube best practices recommend 3 to 5 targeted hashtags.")

        is_compliant = len(errors) == 0
        return is_compliant, errors, warnings

    def save_description(self, desc: VideoDescription) -> int:
        """Persist video description to the database."""
        return self.db.save_video_description(
            channel_id=desc.channel_id,
            channel_name=desc.channel_name,
            topic=desc.topic,
            primary_keyword=desc.primary_keyword,
            full_text=desc.full_text,
            character_count=desc.character_count,
            data=desc.to_dict(),
        )

    def get_channel_descriptions(self, channel_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve previously saved video descriptions for a channel."""
        return self.db.get_video_descriptions(channel_id=channel_id, limit=limit)


# Default singleton instance
description_studio = DescriptionStudio()
