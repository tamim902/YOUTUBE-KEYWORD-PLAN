"""Research intelligence module for YouTube Keyword Finder.

Provides transparent relevance scoring, topic clustering, and audit-grade research session summaries.
"""

from src.intelligence.scoring import RelevanceBreakdown, RelevanceScorer, ScoringWeights, default_scorer
from src.intelligence.clustering import TopicCluster, TopicClusteringEngine, default_clusterer
from src.intelligence.summary import ResearchSummary
from src.intelligence.opportunities import (
    ContentBriefGenerator,
    ContentGapDetector,
    OpportunityScorer,
    TitleHookWorkshop,
    TopicOverlapDetector,
    VideoTopicGenerator,
)
from src.intelligence.product_finder import (
    NicheProductPipeline,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
    infer_product_category,
)
from src.intelligence.monitor import (
    ChangeAlertDetector,
    HistoricalAnalyticsAggregator,
    ResearchComparisonEngine,
    ResearchSchedulerService,
)
from src.intelligence.product_planner import (
    AffiliateBriefGenerator,
    ContentFormatRecommender,
    OpportunityScorerV14,
    ProductComparisonEngine,
)
from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.intelligence.seo_engine import SeoEngine, seo_engine
from src.intelligence.description_studio import DescriptionStudio, description_studio
from src.intelligence.gap_finder import GapFinder, gap_finder
from src.intelligence.daily_engine import DailyOpportunityEngine, daily_opportunity_engine
from src.intelligence.notification import NotificationService, notification_service
from src.intelligence.audit_engine import AuditEngine, audit_engine
from src.intelligence.growth_engine import GrowthEngine, growth_engine
from src.intelligence.strategy_engine import ContentStrategyAutopilot, content_strategy_autopilot
from src.intelligence.validation_engine import TopicValidationEngine, topic_validation_engine
from src.intelligence.research_memory import (
    ResearchMemoryEngine,
    MemoryRecord,
    MemoryType,
    MemoryStatus,
    SimilarityType,
    DuplicateMatch,
    MemoryRecommendation,
    FeedbackStatus,
    UserPerformanceRating,
    PerformanceInsightsSummary,
)

__all__ = [
    "RelevanceBreakdown",
    "RelevanceScorer",
    "ScoringWeights",
    "default_scorer",
    "TopicCluster",
    "TopicClusteringEngine",
    "default_clusterer",
    "ResearchSummary",
    "ContentGapDetector",
    "OpportunityScorer",
    "VideoTopicGenerator",
    "TitleHookWorkshop",
    "ContentBriefGenerator",
    "TopicOverlapDetector",
    "ProductExtractor",
    "ProductMatcher",
    "ProductOpportunityScorer",
    "NicheProductPipeline",
    "infer_product_category",
    "OpportunityScorerV14",
    "ContentFormatRecommender",
    "AffiliateBriefGenerator",
    "ProductComparisonEngine",
    "ResearchComparisonEngine",
    "ChangeAlertDetector",
    "HistoricalAnalyticsAggregator",
    "ResearchSchedulerService",
    "ChannelManager",
    "channel_manager",
    "SeoEngine",
    "seo_engine",
    "DescriptionStudio",
    "description_studio",
    "GapFinder",
    "gap_finder",
    "DailyOpportunityEngine",
    "daily_opportunity_engine",
    "NotificationService",
    "notification_service",
    "AuditEngine",
    "audit_engine",
    "GrowthEngine",
    "growth_engine",
    "ContentStrategyAutopilot",
    "content_strategy_autopilot",
    "TopicValidationEngine",
    "topic_validation_engine",
    "ResearchMemoryEngine",
    "MemoryRecord",
    "MemoryType",
    "MemoryStatus",
    "SimilarityType",
    "DuplicateMatch",
    "MemoryRecommendation",
    "FeedbackStatus",
    "UserPerformanceRating",
    "PerformanceInsightsSummary",
]


