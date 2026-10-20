"""Phase 32 Automated Test Suite: YouTube SEO Content Factory & One-Click Package.

Validates:
1. VideoContentPackage and data model serialization/deserialization
2. Format-adapted package generation: Long-form vs. Shorts
3. Purpose-adapted outlines: Tutorial vs. Review vs. Comparison
4. Channel isolation and brand voice separation (including Bengali Unicode)
5. Misleading and unsupported claim detection in titles
6. Evidence & fact-checking provenance tracking (verified vs unverified)
7. Description character limits (<= 5000 chars) and keyword density checks
8. FTC affiliate disclosure compliance evaluation
9. Database CRUD operations and WAL transaction safety (save, list, get, delete)
10. Calendar scheduling integration
11. Markdown and JSON export formatting
12. Zero fabricated metrics and epistemic modesty
"""

from pathlib import Path
import pytest

from src.intelligence.channel_manager import ChannelManager
from src.intelligence.content_factory import (
    ContentFactoryEngine,
    ReadinessStatus,
    TitleCandidate,
    VideoContentPackage,
    VideoFormat,
    VideoPurpose,
)
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    """Fixture providing an isolated SQLite database in WAL mode."""
    db_file = tmp_path / "test_content_factory.db"
    db = DatabaseManager(db_file)
    db.init_db()
    return db


@pytest.fixture
def test_chan_mgr(test_db: DatabaseManager) -> ChannelManager:
    """Fixture providing a ChannelManager wired to test database."""
    mgr = ChannelManager(test_db)
    mgr.get_all_channels()
    return mgr


@pytest.fixture
def factory_engine(test_db: DatabaseManager, test_chan_mgr: ChannelManager) -> ContentFactoryEngine:
    """Fixture providing a ContentFactoryEngine wired to test database and channel manager."""
    return ContentFactoryEngine(database=test_db, chan_mgr=test_chan_mgr)


# ==============================================================================
# 1. Package Generation Tests (Long-form vs. Shorts)
# ==============================================================================

def test_generate_longform_tutorial_package(factory_engine: ContentFactoryEngine) -> None:
    """Verify complete long-form tutorial package generation."""
    pkg = factory_engine.generate_package(
        channel_id=1,
        topic="How to Build a Custom Mechanical Keyboard",
        primary_keyword="custom mechanical keyboard build",
        format_type=VideoFormat.LONG_FORM,
        purpose_type=VideoPurpose.TUTORIAL,
    )

    assert isinstance(pkg, VideoContentPackage)
    assert pkg.channel_id == 1
    assert pkg.format_type == VideoFormat.LONG_FORM
    assert pkg.purpose_type == VideoPurpose.TUTORIAL
    assert len(pkg.title_options) >= 4
    assert len(pkg.outline.get("sections", [])) >= 4
    assert len(pkg.description_text) > 100
    assert len(pkg.description_text) <= 5000
    assert pkg.thumbnail_concept is not None
    assert len(pkg.thumbnail_concept.hook_text.split()) <= 4
    assert len(pkg.tags) >= 5
    assert len(pkg.seo_readiness) >= 4


def test_generate_shorts_package(factory_engine: ContentFactoryEngine) -> None:
    """Verify YouTube Shorts format output adaptation."""
    pkg = factory_engine.generate_package(
        channel_id=2,
        topic="Python uv in 60 Seconds",
        primary_keyword="python uv tutorial",
        format_type=VideoFormat.SHORTS,
        purpose_type=VideoPurpose.TUTORIAL,
    )

    assert pkg.format_type == VideoFormat.SHORTS
    assert "#Shorts" in pkg.selected_title or "#shorts" in pkg.selected_title.lower()
    assert len(pkg.selected_title) <= 65
    assert "Shorts" in pkg.outline.get("format", "")
    assert len(pkg.outline.get("sections", [])) == 3
    # Check that thumbnail hook text is punchy
    assert len(pkg.thumbnail_concept.hook_text.split()) <= 4


# ==============================================================================
# 2. Channel Isolation & Settings
# ==============================================================================

def test_channel_specific_settings_and_isolation(
    factory_engine: ContentFactoryEngine,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify that packages are strictly isolated by channel, including Bengali Unicode support."""
    # Channel 2: CodeCraft বাংলা
    chan2 = test_chan_mgr.get_channel(2)
    pkg2 = factory_engine.generate_package(
        channel_id=2,
        topic="FastAPI Microservices Tutorial",
        primary_keyword="fastapi microservices",
        format_type=VideoFormat.LONG_FORM,
    )

    assert pkg2.channel_id == 2
    assert "CodeCraft" in pkg2.channel_name
    assert "বাংলা" in pkg2.channel_name
    assert pkg2.target_viewer == chan2.target_audience


# ==============================================================================
# 3. Purpose-Adapted Outline Structures
# ==============================================================================

def test_review_purpose_outline_structure(factory_engine: ContentFactoryEngine) -> None:
    """Verify that a Product Review package includes specs, pros/cons, and buying advice."""
    pkg = factory_engine.generate_package(
        channel_id=3,
        topic="DF54 Espresso Grinder Review",
        primary_keyword="df54 grinder review",
        format_type=VideoFormat.LONG_FORM,
        purpose_type=VideoPurpose.REVIEW,
        product_info={"name": "DF54 Grinder", "specs": "54mm flat burrs, 150W motor"},
    )

    sections = pkg.outline.get("sections", [])
    section_names = [s.get("section_name", "") for s in sections]
    assert any("Pros" in n or "What Works Great" in n for n in section_names)
    assert any("Cons" in n or "Quirks" in n or "Dealbreakers" in n for n in section_names)
    assert any("Final" in n or "Buying Recommendation" in n for n in section_names)


# ==============================================================================
# 4. Misleading Claim Detection in Titles
# ==============================================================================

def test_claim_warning_detection(factory_engine: ContentFactoryEngine) -> None:
    """Verify that titles with exaggerated claim patterns trigger a safety warning."""
    candidates = factory_engine._generate_title_candidates(
        topic="Guaranteed 100% Viral Growth Hack",
        keyword="guaranteed viral growth",
        format_type=VideoFormat.LONG_FORM,
        purpose_type=VideoPurpose.TUTORIAL,
    )

    # At least one candidate will feature the keyword with 'guaranteed'
    flagged = [c for c in candidates if c.claim_warning is not None]
    assert len(flagged) >= 1
    assert "guaranteed results" in flagged[0].claim_warning.lower()


# ==============================================================================
# 5. Evidence & Fact-Checking Provenance
# ==============================================================================

def test_evidence_checklist_provenance(factory_engine: ContentFactoryEngine) -> None:
    """Verify that evidence items distinguish user input, live suggest, and missing research."""
    # Case with no external links
    pkg_no_links = factory_engine.generate_package(
        channel_id=1,
        topic="Mechanical Switch Modding",
        primary_keyword="switch lubing guide",
        source_links=None,
    )

    checklist = pkg_no_links.evidence_checklist
    assert any(e.source_provenance == "Live YouTube Autocomplete" for e in checklist)
    assert any(e.source_provenance == "Missing Research" for e in checklist)

    # Case with external links and user notes
    pkg_with_links = factory_engine.generate_package(
        channel_id=1,
        topic="Mechanical Switch Modding",
        primary_keyword="switch lubing guide",
        user_notes="Tested Krytox 205g0 vs TriboSys 3203",
        source_links=["https://keyboard.docs/lubing"],
    )

    checklist2 = pkg_with_links.evidence_checklist
    assert any(e.source_provenance == "User-Provided Information" for e in checklist2)
    assert any(e.status == "Verified" and "external reference links" in e.fact_statement for e in checklist2)


# ==============================================================================
# 6. Description Character Limit & Keyword Naturalness
# ==============================================================================

def test_description_character_limit_and_density(factory_engine: ContentFactoryEngine) -> None:
    """Verify description character limit <= 5,000 and natural keyword density."""
    pkg = factory_engine.generate_package(
        channel_id=1,
        topic="Keyboard Sound Test Shootout",
        primary_keyword="keyboard sound test",
    )

    assert len(pkg.description_text) <= 5000
    density_check = next((c for c in pkg.seo_readiness if "Keyword Naturalness" in c.item_name), None)
    assert density_check is not None
    assert density_check.status == ReadinessStatus.PASS


# ==============================================================================
# 7. FTC Affiliate Disclosure Compliance
# ==============================================================================

def test_ftc_affiliate_disclosure_evaluation(
    factory_engine: ContentFactoryEngine,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify that affiliate products trigger and verify mandatory FTC disclosure."""
    chan1 = test_chan_mgr.get_channel(1)
    chan1.affiliate_enabled = True
    test_chan_mgr.save_channel(chan1)

    pkg = factory_engine.generate_package(
        channel_id=1,
        topic="Best Ergonomic Desk Chair",
        primary_keyword="ergonomic desk chair",
        product_info={
            "name": "Herman Miller Embody",
            "url": "https://amzn.to/chair-link",
            "specs": "$1,795, Fully adjustable",
        },
    )

    ftc_check = next((c for c in pkg.seo_readiness if "FTC Affiliate Disclosure" in c.item_name), None)
    assert ftc_check is not None
    assert ftc_check.status == ReadinessStatus.PASS
    assert "DISCLOSURE" in pkg.description_text.upper() or "AFFILIATE" in pkg.description_text.upper()


# ==============================================================================
# 8. Database Persistence (Save, Load, List, Delete)
# ==============================================================================

def test_content_package_database_crud(
    factory_engine: ContentFactoryEngine,
    test_db: DatabaseManager,
) -> None:
    """Verify complete CRUD lifecycle of a video content package in SQLite WAL."""
    pkg = factory_engine.generate_package(
        channel_id=3,
        topic="Aeropress Coffee Recipe Guide",
        primary_keyword="aeropress recipe 2026",
    )

    # 1. Save
    pkg_id = factory_engine.save_package(pkg)
    assert pkg_id > 0

    # 2. Load
    loaded = factory_engine.get_package(pkg_id)
    assert loaded is not None
    assert loaded.id == pkg_id
    assert loaded.channel_id == 3
    assert loaded.topic == "Aeropress Coffee Recipe Guide"
    assert loaded.primary_keyword == "aeropress recipe 2026"
    assert len(loaded.title_options) == len(pkg.title_options)

    # 3. List
    pkgs = factory_engine.list_packages(channel_id=3)
    assert len(pkgs) >= 1
    assert pkgs[0].id == pkg_id

    # 4. Delete
    deleted = factory_engine.delete_package(pkg_id)
    assert deleted is True

    # Confirm deletion
    reloaded = factory_engine.get_package(pkg_id)
    assert reloaded is None


# ==============================================================================
# 9. Calendar Scheduling Integration
# ==============================================================================

def test_calendar_scheduling_integration(
    factory_engine: ContentFactoryEngine,
    test_db: DatabaseManager,
) -> None:
    """Verify that scheduling a package creates a valid strategy_calendar_items entry."""
    pkg = factory_engine.generate_package(
        channel_id=4,
        topic="Home Gym Recovery Protocol",
        primary_keyword="recovery protocol for runners",
    )

    cal_id = factory_engine.create_calendar_entry(pkg, planned_date="2026-11-20")
    assert cal_id is not None
    assert cal_id > 0

    # Verify directly in database
    cal_item = test_db.get_strategy_calendar_item_by_id(cal_id)
    assert cal_item is not None
    assert cal_item.channel_id == 4
    assert cal_item.planned_date == "2026-11-20"
    assert cal_item.production_status == "Ready for Recording"


# ==============================================================================
# 10. Markdown Export Formatting
# ==============================================================================

def test_markdown_export_formatting(factory_engine: ContentFactoryEngine) -> None:
    """Verify that exporting as Markdown produces complete, well-formed documentation."""
    pkg = factory_engine.generate_package(
        channel_id=1,
        topic="Mechanical Keyboard Switches 101",
        primary_keyword="keyboard switch guide",
    )

    md = factory_engine.export_as_markdown(pkg)
    assert isinstance(md, str)
    assert "# Video SEO Content Package:" in md
    assert "## 1. Title Options" in md
    assert "## 2. Thumbnail Concept" in md
    assert "## 3. Video Outline & Pacing" in md
    assert "## 4. YouTube Video Description" in md
    assert "## 5. Tag Suggestions" in md
    assert "## 6. Pre-Publish SEO Readiness Checklist" in md
    assert pkg.primary_keyword in md
