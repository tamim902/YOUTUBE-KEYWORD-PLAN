"""Channel Portfolio and Profile Manager (Phase 22 Part 1).

Provides centralized management for the four distinct channel workspaces:
- Channel profile configuration and persistence
- Validation of channel metadata, niches, and URLs
- Keyword and topic exclusion checking
- Channel-specific SEO and research settings
"""

from typing import List, Optional, Tuple

from src.models.channel import ChannelProfile, get_default_four_channels
from src.storage.database import DatabaseManager, db_manager


class ChannelManager:
    """Manages channel profiles, validation, and content filtering."""

    def __init__(self, database: Optional[DatabaseManager] = None) -> None:
        self.db = database or db_manager

    def get_all_channels(self) -> List[ChannelProfile]:
        """Retrieve all 4 channel profiles from database. If missing, seed defaults."""
        profiles = self.db.get_channel_profiles()
        if len(profiles) < 4:
            # Seed any missing channels
            defaults = get_default_four_channels()
            existing_ids = {p.id for p in profiles if p.id is not None}
            for d in defaults:
                if d.id not in existing_ids:
                    self.db.save_channel_profile(d)
            profiles = self.db.get_channel_profiles()
        return profiles

    def get_channel(self, channel_id: int) -> Optional[ChannelProfile]:
        """Retrieve a specific channel profile by its ID (1-4)."""
        profile = self.db.get_channel_profile(channel_id)
        if not profile and 1 <= channel_id <= 4:
            defaults = get_default_four_channels()
            for d in defaults:
                if d.id == channel_id:
                    self.db.save_channel_profile(d)
                    return d
        return profile

    def save_channel(self, profile: ChannelProfile) -> int:
        """Persist channel profile updates after validation."""
        valid, errors = self.validate_channel(profile)
        if not valid:
            raise ValueError(f"Channel profile validation failed: {'; '.join(errors)}")
        return self.db.save_channel_profile(profile)

    def validate_channel(self, profile: ChannelProfile) -> Tuple[bool, List[str]]:
        """Validate channel profile requirements."""
        errors: List[str] = []
        if not profile.channel_name or not profile.channel_name.strip():
            errors.append("Channel name cannot be empty.")
        if not profile.channel_niche or not profile.channel_niche.strip():
            errors.append("Channel niche cannot be empty.")
        if not profile.target_country or len(profile.target_country.strip()) < 2:
            errors.append("Target country must be a valid 2-letter country code.")
        if not profile.target_language or len(profile.target_language.strip()) < 2:
            errors.append("Target language must be a valid 2-letter language code.")
        
        url_valid, url_msg = profile.validate_channel_url()
        if not url_valid:
            errors.append(url_msg)

        return len(errors) == 0, errors

    def filter_keywords_for_channel(self, keywords: List[str], channel: ChannelProfile) -> List[str]:
        """Filter out any keywords that match channel exclusions."""
        filtered = []
        for kw in keywords:
            is_excluded, _ = channel.is_excluded(kw)
            if not is_excluded:
                filtered.append(kw)
        return filtered


# Default singleton instance
channel_manager = ChannelManager()
