"""Unit and integration tests for Phase 24: YouTube Analytics & Four-Channel Growth Intelligence."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.models.channel import ChannelProfile
from src.models.analytics import (
    AnalyticsAuthStatus,
    ChannelAnalyticsOverview,
    ChannelOAuthCredentials,
    GrowthRecommendation,
    MetricComparison,
    PublishingExperiment,
    VideoAnalyticsItem,
)
from src.providers.youtube_analytics import (
    STANDARD_SCOPES,
    YouTubeAnalyticsProvider,
)
from src.intelligence.growth_engine import GrowthEngine
from src.storage.database import DatabaseManager
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    EXTENDED_NAVIGATION_PAGES,
    EXTENDED_PAGE_SECTION_MAP,
    PAGE_ANALYTICS,
    PAGE_LABEL_CLEAN_MAP,
    PHASE24_PAGES,
)


@pytest.fixture
def test_channel():
    """Sample channel profile for testing."""
    return ChannelProfile(
        id=1,
        channel_name="Tech Review Lab",
        channel_handle="@techreviewlab",
        channel_niche="Mechanical Keyboards",
        sub_niches=["Custom Keyboards", "Switches"],
        target_audience="Keyboard enthusiasts",
        affiliate_enabled=True,
    )


@pytest.fixture
def mock_db(tmp_path):
    """Temporary SQLite database manager for isolated testing."""
    db_file = tmp_path / "test_analytics.db"
    db = DatabaseManager(db_path=db_file)
    db.init_db()
    return db


@pytest.fixture
def analytics_provider(mock_db):
    """YouTubeAnalyticsProvider backed by test database."""
    return YouTubeAnalyticsProvider(database=mock_db)


@pytest.fixture
def growth_engine(mock_db):
    """GrowthEngine backed by test database."""
    return GrowthEngine(database=mock_db)


# ==============================================================================
# 1. OAuth 2.0 Construction & Scope Validation
# ==============================================================================

def test_oauth_authorization_url_construction(analytics_provider):
    """Verify official Google OAuth consent URL structure and minimal necessary scopes."""
    url = analytics_provider.build_authorization_url(
        channel_id=1,
        client_id="test-client-id-123.apps.googleusercontent.com",
        redirect_uri="http://localhost:8501",
        state="chan_1_state",
    )
    assert "https://accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=test-client-id-123" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8501" in url or "redirect_uri=http://localhost:8501" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=chan_1_state" in url
    # Verify minimal read-only scopes
    for scope in STANDARD_SCOPES:
        assert scope.replace(":", "%3A").replace("/", "%2F") in url or scope in url


def test_token_credentials_security_and_masking():
    """Verify that tokens and client secrets are masked in string representations and never leak."""
    creds = ChannelOAuthCredentials(
        channel_id=1,
        channel_name="Tech Channel",
        client_id="12345.apps.googleusercontent.com",
        client_secret="GOCSPX-super-secret-key-12345",
        access_token="ya29.secret_access_token_abcde",
        refresh_token="1//secret_refresh_token_xyz",
        auth_status=AnalyticsAuthStatus.AUTHORIZED,
    )
    repr_str = repr(creds)
    # Ensure sensitive tokens are NOT printed in plain text
    assert "ya29.secret_access_token_abcde" not in repr_str
    assert "1//secret_refresh_token_xyz" not in repr_str
    assert "super-secret-key" not in repr_str

    # Test mask_secret
    masked = creds.mask_secret()
    assert masked.startswith("GOC...")
    assert masked.endswith("345")
    assert "super-secret-key" not in masked


# ==============================================================================
# 2. Token Exchange & API Mocking
# ==============================================================================

@patch("requests.post")
def test_exchange_authorization_code_success(mock_post, analytics_provider, mock_db):
    """Test successful OAuth code exchange and local SQLite persistence."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "ya29.test_access_token",
        "refresh_token": "1//test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_post.return_value = mock_resp

    success, msg, creds = analytics_provider.exchange_authorization_code(
        channel_id=1,
        channel_name="Tech Review Lab",
        client_id="client-123",
        client_secret="secret-456",
        code="auth-code-789",
        redirect_uri="http://localhost:8501",
    )

    assert success is True
    assert creds is not None
    assert creds.auth_status == AnalyticsAuthStatus.AUTHORIZED
    assert creds.access_token == "ya29.test_access_token"

    # Verify persisted in SQLite
    saved_creds = mock_db.get_channel_credentials(1)
    assert saved_creds is not None
    assert saved_creds.client_id == "client-123"
    assert saved_creds.access_token == "ya29.test_access_token"
    assert saved_creds.refresh_token == "1//test_refresh_token"


@patch("requests.post")
def test_exchange_authorization_code_failure(mock_post, analytics_provider):
    """Test failed authorization code exchange handling."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": "invalid_grant", "error_description": "Code has expired."}
    mock_post.return_value = mock_resp

    success, msg, creds = analytics_provider.exchange_authorization_code(
        channel_id=1,
        channel_name="Tech Review Lab",
        client_id="client-123",
        client_secret="secret-456",
        code="expired-code",
        redirect_uri="http://localhost:8501",
    )

    assert success is False
    assert creds is None
    assert "invalid_grant" in msg or "expired" in msg.lower()


# ==============================================================================
# 3. Disconnect & Revocation
# ==============================================================================

@patch("requests.post")
def test_revoke_authorization(mock_post, analytics_provider, mock_db):
    """Test disconnecting channel and deleting credentials from SQLite."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    creds = ChannelOAuthCredentials(
        channel_id=1,
        channel_name="Tech Review Lab",
        client_id="client-1",
        access_token="token-1",
        refresh_token="ref-1",
        auth_status=AnalyticsAuthStatus.AUTHORIZED,
    )
    mock_db.save_channel_credentials(creds)
    assert mock_db.get_channel_credentials(1) is not None

    success, msg = analytics_provider.revoke_authorization(1)
    assert success is True
    # Verify deleted from SQLite
    assert mock_db.get_channel_credentials(1) is None


# ==============================================================================
# 4. Mathematical Zero-Denominator Protection Tests
# ==============================================================================

def test_metric_comparison_zero_denominator_protection(growth_engine):
    """Test mathematical zero-denominator protection (no ZeroDivisionError or infinite %)."""
    # Comparison value is 0, current is 150
    cmp_zero = growth_engine.compute_metric_comparison(
        name="Views",
        current_value=150.0,
        comparison_value=0.0,
        format_type="integer",
    )
    assert cmp_zero.percentage_change is None
    assert cmp_zero.absolute_change == 150.0
    assert cmp_zero.change_direction == "increased"
    assert "prior period was 0" in cmp_zero.display_change

    # Both values are 0
    cmp_both_zero = growth_engine.compute_metric_comparison(
        name="Views",
        current_value=0.0,
        comparison_value=0.0,
        format_type="integer",
    )
    assert cmp_both_zero.percentage_change is None
    assert cmp_both_zero.change_direction == "unchanged"
    assert "no change" in cmp_both_zero.display_change.lower()


def test_metric_comparison_standard_percentage(growth_engine):
    """Test standard percentage change calculation when comparison baseline > 0."""
    cmp_std = growth_engine.compute_metric_comparison(
        name="Views",
        current_value=250.0,
        comparison_value=200.0,
        format_type="integer",
    )
    assert cmp_std.absolute_change == 50.0
    assert cmp_std.percentage_change == 25.0
    assert cmp_std.change_direction == "increased"
    assert "+50" in cmp_std.display_change
    assert "+25.0%" in cmp_std.display_change


def test_metric_comparison_missing_data_handling(growth_engine):
    """Test that missing/None values are cleanly labeled as unavailable without fake zeros."""
    cmp_none = growth_engine.compute_metric_comparison(
        name="Impressions",
        current_value=None,
        comparison_value=100.0,
    )
    assert cmp_none.is_available is False
    assert cmp_none.percentage_change is None
    assert cmp_none.display_change == "N/A (Missing data)"
    assert cmp_none.change_direction == "unavailable"


# ==============================================================================
# 5. Four-Channel Isolation Tests
# ==============================================================================

def test_four_channel_analytics_isolation(mock_db):
    """Ensure credentials and data for Channel 1 cannot bleed into Channels 2, 3, or 4."""
    creds_ch1 = ChannelOAuthCredentials(
        channel_id=1,
        channel_name="Channel One",
        client_id="client-ch1",
        access_token="token-ch1",
        auth_status=AnalyticsAuthStatus.AUTHORIZED,
    )
    creds_ch2 = ChannelOAuthCredentials(
        channel_id=2,
        channel_name="Channel Two",
        client_id="client-ch2",
        access_token="token-ch2",
        auth_status=AnalyticsAuthStatus.NOT_CONNECTED,
    )
    mock_db.save_channel_credentials(creds_ch1)
    mock_db.save_channel_credentials(creds_ch2)

    retrieved_1 = mock_db.get_channel_credentials(1)
    retrieved_2 = mock_db.get_channel_credentials(2)
    retrieved_3 = mock_db.get_channel_credentials(3)

    assert retrieved_1.client_id == "client-ch1"
    assert retrieved_1.auth_status == AnalyticsAuthStatus.AUTHORIZED

    assert retrieved_2.client_id == "client-ch2"
    assert retrieved_2.auth_status == AnalyticsAuthStatus.NOT_CONNECTED

    assert retrieved_3 is None


# ==============================================================================
# 6. Topic & Keyword Performance Learning & Epistemic Modesty
# ==============================================================================

def test_topic_keyword_learning_and_causation_caution(growth_engine):
    """Test topic aggregation and verify epistemic correlation caveats are explicitly present."""
    videos = [
        VideoAnalyticsItem(
            video_id="v1",
            channel_id=1,
            title="Custom Mechanical Keyboards Sound Test",
            published_at="2026-01-10",
            video_format="Long-form",
            views=1200,
        ),
        VideoAnalyticsItem(
            video_id="v2",
            channel_id=1,
            title="Custom Mechanical Keyboards Guide",
            published_at="2026-02-15",
            video_format="Long-form",
            views=1800,
        ),
    ]

    results = growth_engine.correlate_topics_and_keywords(channel_id=1, videos=videos)
    assert len(results) > 0
    top_cluster = results[0]
    assert top_cluster["total_views"] == 3000
    assert top_cluster["average_views"] == 1500.0
    # Verify correlation caution is explicitly returned
    assert "causation" in top_cluster["epistemic_warning"].lower()


# ==============================================================================
# 7. Growth Coach 5-Point Evidence Framework Tests
# ==============================================================================

def test_growth_coach_starter_plan_for_new_channel(growth_engine, test_channel):
    """Verify Growth Coach outputs starter strategy when insufficient historical data exists."""
    recs = growth_engine.generate_growth_recommendations(test_channel, overview=None, videos=[])
    assert len(recs) >= 1
    starter = recs[0]
    assert starter.category == "Starter Strategy"
    # Verify all 5 points of the evidence framework are populated
    assert bool(starter.observed_fact)
    assert bool(starter.supporting_evidence)
    assert bool(starter.uncertainty_and_confounders)
    assert bool(starter.suggested_action)
    assert bool(starter.success_measurement)


def test_growth_coach_5_point_framework_with_data(growth_engine, test_channel):
    """Verify Growth Coach produces recommendations adhering to all 5 required points."""
    videos = [
        VideoAnalyticsItem(video_id="v1", channel_id=1, title="Switches Guide", published_at="2026-01-01", video_format="Long-form", views=2000),
        VideoAnalyticsItem(video_id="v2", channel_id=1, title="Switches Review", published_at="2026-01-15", video_format="Long-form", views=3500),
        VideoAnalyticsItem(video_id="v3", channel_id=1, title="Quick Typing Short", published_at="2026-02-01", video_format="Shorts", views=800),
    ]
    recs = growth_engine.generate_growth_recommendations(test_channel, overview=None, videos=videos)
    assert len(recs) >= 2
    for r in recs:
        assert len(r.observed_fact) > 5
        assert len(r.supporting_evidence) > 5
        assert len(r.uncertainty_and_confounders) > 5
        assert len(r.suggested_action) > 5
        assert len(r.success_measurement) > 5


# ==============================================================================
# 8. Publishing Experiments Tracking Tests
# ==============================================================================

def test_publishing_experiments_lifecycle_and_confounding_factors(mock_db, growth_engine):
    """Test creating, storing, evaluating, and labeling confounding factors in experiments."""
    exp = PublishingExperiment(
        id=None,
        channel_id=1,
        experiment_name="Title Truncation Optimization",
        video_id="dQw4w9WgXcQ",
        video_title="Before Title Change",
        experiment_type="Title Revision",
        hypothesis="Front-loading the keyword will increase click-through.",
        status="Running",
        started_at="2026-03-01T00:00:00Z",
        pre_metrics={"views": 500, "impressions_ctr": 4.0},
    )

    exp_id = mock_db.save_publishing_experiment(exp)
    assert exp_id > 0

    # Retrieve running experiment
    running_exps = mock_db.get_publishing_experiments(channel_id=1, status="Running")
    assert len(running_exps) == 1
    assert running_exps[0]["experiment_name"] == "Title Truncation Optimization"

    # Evaluate experiment post-metrics
    evaluated = growth_engine.evaluate_publishing_experiment(
        exp,
        post_metrics={"views": 850, "impressions_ctr": 5.8},
    )
    mock_db.save_publishing_experiment(evaluated)

    completed_exps = mock_db.get_publishing_experiments(channel_id=1, status="Completed")
    assert len(completed_exps) == 1
    comp_rec = completed_exps[0]
    assert comp_rec["is_conclusive"] is True
    assert len(comp_rec["confounding_factors"]) > 0
    assert "causality cannot be definitively proven" in comp_rec["outcome_conclusion"].lower()


# ==============================================================================
# 9. Daily Morning Growth Brief Integration Tests
# ==============================================================================

def test_morning_growth_brief_generation(growth_engine, test_channel):
    """Test synthesizing channel analytics and growth recommendations into a morning brief."""
    brief = growth_engine.generate_morning_growth_brief(
        channel=test_channel,
        overview=None,
        videos=[],
    )
    assert brief["channel_id"] == 1
    assert brief["channel_name"] == "Tech Review Lab"
    assert "OAuth Unconnected" in brief["analytics_status"] or "Public" in brief["analytics_status"]
    assert bool(brief["top_recommended_action"])
    assert bool(brief["recommendation_evidence"])


# ==============================================================================
# 10. Navigation Contract Integrity Tests
# ==============================================================================

def test_navigation_contract_and_extended_pages():
    """Verify ALL_NAVIGATION_PAGES remains exactly 14 base destinations and PAGE_ANALYTICS is extended."""
    assert len(ALL_NAVIGATION_PAGES) == 14
    assert PAGE_ANALYTICS not in ALL_NAVIGATION_PAGES
    assert PAGE_ANALYTICS in PHASE24_PAGES
    assert PAGE_ANALYTICS in EXTENDED_NAVIGATION_PAGES
    assert PAGE_ANALYTICS in PAGE_LABEL_CLEAN_MAP
    assert PAGE_ANALYTICS in EXTENDED_PAGE_SECTION_MAP
