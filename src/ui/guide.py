"""Intelligent User Guide, Contextual Help System, Smart Workflow Assistant & Interactive Tours.

Provides:
- Complete documentation covering all 11 required points for all 10 major application sections.
- Contextual help drawers and callouts for seamless in-page assistance.
- Interactive Guided Tours with Next, Back, Skip, Finish controls and element highlights.
- 7-Goal First-Run Onboarding Engine with tailored workflows.
- 3 Structured Smart Workflow Plans (Keyword Research, Niche Product Research, Competitor Research).
- Deterministic Next-Best-Action guidance engine based on actual application state.
- Real-condition workflow progress checklist tracking.
- Scoped guidance preference resets preserving all research datasets.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import streamlit as st

from src.storage import db_manager


# ==============================================================================
# 1. Comprehensive User Guide Documentation Database (All 11 Mandatory Points)
# ==============================================================================

USER_GUIDE_SECTIONS: Dict[str, Dict[str, Any]] = {
    "keyword_discovery": {
        "title": "🔍 Keyword Discovery & Autocomplete Expansion",
        "category": "Core Keyword Research",
        "summary": "Discover authentic viewer queries directly from YouTube's live autocomplete suggestion API without fabricated search volume estimates.",
        "when_to_use": "Use when starting research on a new topic, looking for long-tail keyword variations, or mapping audience demand hierarchically.",
        "prerequisites": "A broad seed keyword (e.g. 'wireless earbuds', 'notion setup', 'python tutorial'). No API key required.",
        "steps": [
            "Navigate to '🔍 New Keyword Research' from the sidebar.",
            "Enter your seed keyword into the primary query field.",
            "Select target Country (default: US) and Language (default: en).",
            "Choose Discovery Depth (Depth 1 = seed suggestions, Depth 2 = recursive expansion).",
            "Select Search Mode: 'Direct Autocomplete' for instant seed suggestions, or 'Recursive Tree Expansion' for multi-level mapping.",
            "Optionally enable 'Smart Pattern Variations' to inject high-intent modifiers (best, review, vs, for beginners).",
            "Click 'Start Keyword Research' and monitor real-time query tree expansion.",
            "Filter discovered keywords by tail length (Short, Medium, Long-tail) or search intent.",
            "Export results to CSV (UTF-8 BOM) or Excel (.xlsx) with formula injection protection.",
        ],
        "option_choices": {
            "Direct vs. Recursive": "Direct mode queries YouTube once for the seed (~10 suggestions). Recursive mode queries child suggestions to find deep long-tail clusters (up to 150+ keywords).",
            "Alphabetical Expansion": "Appends letters a–z to the seed query to discover niche queries starting with each letter.",
            "Smart Pattern Variations": "Appends commercial, instructional, and comparison prefixes/suffixes.",
        },
        "recommended_defaults": "Recursive Depth 2, Target Country US, Language English, Smart Patterns Enabled. This yields a balanced 80–120 keyword taxonomy within 10–15 seconds.",
        "expected_result": "A structured table of discovered keywords with tail classification, linguistic search intent, discovery query path, and deduplication records.",
        "how_to_interpret": "Keywords with 4+ words are high-intent long-tail opportunities. Transactional and Commercial intent keywords have higher buyer interest; Informational keywords drive broad awareness.",
        "metric_explanations": {
            "Tail Length": "Classifies keywords: Short-tail (1–2 words), Medium-tail (3 words), or Long-tail (4+ words).",
            "Search Intent": "Linguistic classification: Informational (how/what/guide), Commercial (best/review/vs), Transactional (buy/price/coupon), or Navigational.",
            "Discovery Depth": "Level in the recursive suggestion tree where the query was first uncovered.",
        },
        "interpreting_zero_results": "Zero autocomplete suggestions indicates an overly narrow or misspelled seed query. YouTube only suggests phrases that real viewers have typed repeatedly. Broaden your query (e.g. from 'best wireless earbuds under 37 dollars with blue led' to 'wireless earbuds under 50').",
        "common_mistakes": "Using overly narrow seeds (e.g. 'sony wf-1000xm5 best equalizer settings for running in rain') as root queries. Always start broad and let recursive expansion uncover narrow queries.",
        "troubleshooting": "If few results appear, verify network connectivity to YouTube's public suggest API or toggle target language and country to match your seed language.",
        "what_to_do_next": "Select your top discovered keywords and navigate to '🎥 YouTube Video Research' to inspect actual competitor SERP rankings and view counts.",
        "export_and_saving": "Export to UTF-8 BOM CSV or Excel (.xlsx). All outputs are sanitized against formula injection (=, +, -, @). Sessions persist locally in SQLite.",
    },
    "pattern_generator": {
        "title": "🧩 Smart Keyword Pattern Generator",
        "category": "Core Keyword Research",
        "summary": "Deterministic multi-angle query matrix generator applying audience intent templates across commercial, problem-solving, and comparative angles.",
        "when_to_use": "Use when you have a core product or topic and want to generate comprehensive video title concepts and modifier angles systematically.",
        "prerequisites": "A core entity name (e.g. 'mechanical keyboard', 'iphone 16 pro').",
        "steps": [
            "Navigate to '🧩 Pattern Generator' in the sidebar.",
            "Input your root product or subject term.",
            "Select target intent categories (Buying Guide, Problem Solving, Comparison, Speed/Efficiency, Budget).",
            "Choose generation language (English or Bangla multi-script).",
            "Click 'Generate Matrix Variations'.",
            "Inspect variations grouped by category with intent explanations.",
            "Copy individual patterns or export the matrix to spreadsheet format.",
        ],
        "option_choices": {
            "Buying Guide Patterns": "Injects high-conversion buyer modifiers: 'best ... for ...', 'top 5 ... in 2026', 'is ... worth it'.",
            "Comparison Matrix": "Generates 'X vs Y', 'alternatives to X', 'why I switched from X to Y'.",
            "Troubleshooting Angles": "Generates 'how to fix ...', 'common mistakes with ...', 'why ... is not working'.",
        },
        "recommended_defaults": "Enable all 5 intent categories for a complete 360-degree content calendar map.",
        "expected_result": "25–50 high-relevance keyword concepts categorized by viewer psychological stage.",
        "how_to_interpret": "Prioritize Comparison and Buying Guide patterns for high-CPM affiliate videos; prioritize Troubleshooting patterns for evergreen search traffic.",
        "metric_explanations": {
            "Pattern Category": "Intent archetype: Buying Guide, Comparison, Troubleshooting, Beginner, Advanced.",
            "Modifier Density": "Number of high-intent search modifiers applied to the root entity.",
        },
        "interpreting_zero_results": "Zero patterns generated means no intent categories were selected or the root input was empty. Enter a 1–3 word subject noun.",
        "common_mistakes": "Feeding full sentences instead of a concise noun phrase into the root term field.",
        "troubleshooting": "Ensure your entity name is clean without leading punctuation or trailing filler words.",
        "what_to_do_next": "Test these generated patterns in the live Autocomplete tool to see which ones real YouTube viewers search most frequently.",
        "export_and_saving": "Export the generated matrix to CSV or copy all patterns into clipboard with one click.",
    },
    "video_serp": {
        "title": "🎥 YouTube Video Research & Competitor SERP",
        "category": "Competitor & SERP Intelligence",
        "summary": "Inspect real top-ranking YouTube videos, competitor view counts, channel subscriber authority, publication recency, and hidden video tags.",
        "when_to_use": "Use before producing a video to verify whether existing ranking videos are outdated, low-authority, or missing key angles.",
        "prerequisites": "A specific target keyword and optionally a YouTube Data API v3 key in .env for live view count metrics.",
        "steps": [
            "Navigate to '🎥 YouTube Video Research'.",
            "Select a target keyword from your discovered list or enter a custom query.",
            "Choose date range window (e.g. Last 60 Days, Last 6 Months, All Time).",
            "Click 'Analyze YouTube SERP'.",
            "Review Competitor Metrics: Median View Count, Top Channel Authority, Upload Recency Distribution.",
            "Inspect the Tag Cloud to see keywords top-ranking competitors tag in their metadata.",
            "Identify Content Gaps: Look for queries where top videos are >1 year old or have low view counts.",
            "Export SERP analysis to CSV or Excel.",
        ],
        "option_choices": {
            "API Provider Mode": "YouTube Data API v3 provides exact view counts, like counts, and tags. Public Scraper mode operates when no API key is configured.",
            "Date Window": "Last 60 Days isolates recent trending momentum; All Time reveals evergreen authority benchmarks.",
        },
        "recommended_defaults": "Date window: Last 60 Days. This reveals fresh competition rather than 5-year-old viral outliers.",
        "expected_result": "A ranked list of competitor videos, channel subscriber counts, engagement rates, publication dates, and extracted video tags.",
        "how_to_interpret": "If top ranking videos have low view counts (<5,000) or are from small channels (<10,000 subscribers), this represents a high-opportunity search gap.",
        "metric_explanations": {
            "Median View Count": "Middle view count across the top ranking videos, resilient against viral outlier distortion.",
            "Top Channel Authority": "Subscriber tier of ranking creators (Micro, Mid-tier, Macro channels).",
            "Publication Recency": "Percentage of ranking videos published in the selected date window.",
        },
        "interpreting_zero_results": "Zero ranking videos returned indicates an extremely obscure keyword or restrictive date window filter. Widen the date window from 60 Days to All Time.",
        "common_mistakes": "Competing directly against massive established creators on ultra-broad head terms without a distinct angle or specific long-tail hook.",
        "troubleshooting": "If view metrics show zero or fallback, verify your YouTube API key quota in '⚙️ Settings & Data Sources'.",
        "what_to_do_next": "Navigate to '💡 Content Opportunities' to generate an optimized content brief and hook concepts based on competitor weaknesses.",
        "export_and_saving": "Export SERP competitor tables and tag frequency matrices to sanitized Excel (.xlsx) files.",
    },
    "content_opportunities": {
        "title": "💡 Content Opportunities & Hook Workshop",
        "category": "Content Strategy & Planning",
        "summary": "Algorithmic opportunity scoring, topic cluster mapping, and title hook workshop for planning standout YouTube videos.",
        "when_to_use": "Use when deciding which video to film next and crafting compelling click-worthy titles that stand out from competitors.",
        "prerequisites": "A research session with discovered keywords and SERP competitor data.",
        "steps": [
            "Navigate to '💡 Content Opportunities'.",
            "Select an active research session.",
            "Filter opportunities by Opportunity Score (0–100) and Intent.",
            "Inspect the Topic Clusters to see grouped video concepts.",
            "Click on an opportunity card to launch the 'Title Hook Workshop'.",
            "Review generated title variations: Curiosity Gap, Authority Stance, Benefit Driven, Negative Hook.",
            "Review Topic Overlap check to prevent cannibalizing your own existing channel uploads.",
            "Generate and download the production Content Brief.",
        ],
        "option_choices": {
            "Opportunity Score Weighting": "Calculated based on search intent relevance, long-tail specificity, and competitor vulnerability.",
            "Title Hook Archetypes": "Curiosity (creates information gap), Authority (establishes definitive guide), Contrarian (challenges conventional wisdom).",
        },
        "recommended_defaults": "Target opportunities with scores >= 65 for maximum return on production effort.",
        "expected_result": "A prioritized production roadmap with pre-formatted title concepts, target tags, and content briefs.",
        "how_to_interpret": "Higher opportunity scores signify strong audience interest with lower established competitor saturation.",
        "metric_explanations": {
            "Opportunity Score (0–100)": "Weighted score combining keyword intent, long-tail length, competitor weakness, and query recency.",
            "Topic Cluster Density": "Number of tightly coupled long-tail keywords that can be addressed in a single video.",
        },
        "interpreting_zero_results": "Zero opportunities listed means the opportunity score filter threshold is set higher than any discovered item. Lower the score slider to 40.",
        "common_mistakes": "Focusing only on high search volume without checking if competitor videos already answer the query comprehensively.",
        "troubleshooting": "If topic clusters appear fragmented, lower the clustering similarity threshold in settings.",
        "what_to_do_next": "Export the Content Brief into your video production workflow (Notion, Obsidian, or Trello).",
        "export_and_saving": "Download Markdown or PDF-ready Content Briefs including target tags, talking points, and title variations.",
    },
    "product_opportunities": {
        "title": "📦 Niche Product Opportunity Finder (60-Day Gap)",
        "category": "E-Commerce & Commercial Intelligence",
        "summary": "Discovers real commercial products in a niche and searches the last 60 days on YouTube to find products with few or zero matching videos.",
        "when_to_use": "Use when seeking untapped physical products or software to review, sponsor, or create affiliate content for before the market saturates.",
        "prerequisites": "A commercial niche term (e.g. 'Mechanical Keyboards', 'Wireless Earbuds', 'Smart Home Sensors').",
        "steps": [
            "Navigate to '📦 Niche Product Opportunity Finder'.",
            "Enter Niche Name, Target Country, and Research Language.",
            "Set Date Range (defaults to last 60 days: verified recent window).",
            "Select Product Discovery Mode: Curated Catalog, Autocomplete Extraction, or Smart Entity Angles.",
            "Set Search Query Budget and Minimum Research Coverage threshold.",
            "Click 'Start Niche Product Research'.",
            "Examine product classifications: 'Zero Observed Matches', 'Few Observed Matches', 'Active Video Coverage', or 'Insufficient Research'.",
            "Verify product identity by inspecting manufacturer model details.",
            "Review Evidence Cards with source links, query coverage logs, and limitations disclosure.",
            "Export full report to CSV and Excel.",
        ],
        "option_choices": {
            "Minimum Query Coverage": "Requires at least 2–3 distinct queries per product before classifying as 'Zero Observed Matches' to prevent false negatives.",
            "Date Window": "Default 60 days isolates recent upload activity. Can be expanded to 90 or 120 days.",
            "Matching Strictness": "Exact Model Match (strict string matching) vs Flexible Match (fuzzy token matching).",
        },
        "recommended_defaults": "Last 60 Days, Min Coverage = 2 queries, Exact Model Match. Avoids false absence claims while capturing real upload gaps.",
        "expected_result": "A verified catalog of real products with exact count of observed matching videos and transparent research limitations.",
        "how_to_interpret": "Zero Observed Matches means no matching videos were found in your executed queries. It is empirical evidence of low coverage, NOT platform-wide absence.",
        "metric_explanations": {
            "Observed Matching Videos": "Empirical count of videos retrieved matching product model in executed queries within selected date window.",
            "Query Coverage": "Number of distinct search query angles tested for this product.",
            "Evidence Confidence": "Reliability indicator based on verification status and query completeness.",
        },
        "interpreting_zero_results": "Zero Observed Matches is the primary opportunity metric. It represents an upload gap. Verify commercial consumer interest before production.",
        "common_mistakes": "Assuming a product with 0 videos has high demand. Always verify that consumer interest exists before investing in product samples.",
        "troubleshooting": "If products show 'Insufficient Research', increase the query budget or rerun failed queries.",
        "what_to_do_next": "Send promising candidates to '🏷️ Product Opportunity Planner' to formulate affiliate video briefs.",
        "export_and_saving": "Export product opportunity records, evidence logs, and gap classifications to CSV or Excel with formula protection.",
    },
    "product_planner": {
        "title": "🏷️ Product Opportunity Planner & Affiliate Briefs",
        "category": "E-Commerce & Commercial Intelligence",
        "summary": "Affiliate content planning, commission projection, video format recommendation, and FTC-compliant production briefs.",
        "when_to_use": "Use to prioritize commercial products for affiliate video production and construct structured review or comparison scripts.",
        "prerequisites": "A completed Niche Product Research session.",
        "steps": [
            "Navigate to '🏷️ Product Opportunity Planner'.",
            "Select an existing Niche Research Session.",
            "Filter products by category, price tier, and observed video gap.",
            "Select candidate products and click 'Add to Priority Shortlist'.",
            "Configure Affiliate Settings: Estimated Retail Price, Commission Rate (%), and Target Conversion Rate.",
            "Review Recommended Video Format: In-Depth Review, Head-to-Head Comparison, or Round-up Buying Guide.",
            "Generate Affiliate Content Brief with FTC Disclosure checklist.",
            "Export Shortlist and Briefs to CSV or XLSX.",
        ],
        "option_choices": {
            "Video Format Archetypes": "Review (best for standalone zero-match products), Comparison (best for 2 competing products), Round-up (best for 5+ products).",
            "Shortlist Priority": "High (order review sample now), Medium (queue for next month), Low (monitor only).",
        },
        "recommended_defaults": "Commission rate 4% (Amazon Associates benchmark) or 10–15% for direct brand affiliate programs.",
        "expected_result": "A prioritized monetization roadmap with projected earnings per 10k views, comparison angles, and FTC compliance text.",
        "how_to_interpret": "Focus on products with high commission value ($10+ per sale) and low observed YouTube competition for highest affiliate ROI.",
        "metric_explanations": {
            "Projected Earnings / 10k Views": "Estimated affiliate revenue modeled on conversion rate and product commission value.",
            "Video Format Fit": "Heuristic match based on product uniqueness, price tier, and competitor video count.",
        },
        "interpreting_zero_results": "If no products appear in the planner, verify that a niche research session was selected and that products were added to the shortlist.",
        "common_mistakes": "Forgetting FTC affiliate disclosure requirements. Always include spoken and written disclosure in your video description.",
        "troubleshooting": "If retail price is unknown, input an estimated average price based on comparable items in the niche.",
        "what_to_do_next": "Set up an automated monitor in '📡 Research Monitor' to be notified if competitor channels begin covering your shortlisted products.",
        "export_and_saving": "Export shortlisted products and FTC-compliant production briefs directly to CSV or Excel.",
    },
    "research_monitor": {
        "title": "📡 Research Monitor & In-Process Scheduler",
        "category": "Automation & Longitudinal Monitoring",
        "summary": "Automated recurring scans, snapshot differential comparison, change detection alerts, and longitudinal niche analytics.",
        "when_to_use": "Use to track evolving niches over time, detect new product releases, and receive alerts when competitor coverage changes.",
        "prerequisites": "A saved niche research configuration.",
        "steps": [
            "Navigate to '📡 Research Monitor'.",
            "Create a new Saved Research Configuration (Niche, Country, Window, Budget, Filters).",
            "Optionally configure recurring schedule (Daily, Weekly, Monthly, or Manual).",
            "Trigger an on-demand research run or let the in-process scheduler execute automatically.",
            "Navigate to 'Snapshot Comparison' to compare Run A vs Run B.",
            "Review Deltas: Newly Discovered Products, Matching Video Deltas, Score Shifts.",
            "Inspect 'Change Alerts Feed' for critical and high-opportunity notifications.",
            "Analyze 'Historical Trends' charts to observe niche trajectory over time.",
            "Export comparison matrix and run history to CSV or Excel.",
        ],
        "option_choices": {
            "Schedule Frequency": "Weekly is optimal for physical products; Daily for fast-moving tech gadgets; Monthly for evergreen niches.",
            "Alert Sensitivity": "Set minimum score shift (default 15 pts) and minimum video count increase (default 3 videos).",
        },
        "recommended_defaults": "Weekly schedule, Request Budget 50 queries, Alert Sensitivity: Score delta >= 15 pts.",
        "expected_result": "Time-series records of niche evolution with visual diffs and proactive alerts.",
        "how_to_interpret": "A sudden jump in matching videos indicates a product is going viral. A steady zero-match status over months confirms a neglected product.",
        "metric_explanations": {
            "Snapshot Delta": "Change in matching video count or opportunity score between two distinct point-in-time runs.",
            "Alert Severity": "High (major competitor coverage increase), Medium (new product added), Low (minor score shift).",
        },
        "interpreting_zero_results": "Zero diffs between runs indicates the niche has remained stable with no new competitor video uploads detected.",
        "common_mistakes": "Expecting background scans to run when your computer is powered off. The application operates 100% locally on your machine.",
        "troubleshooting": "If runs fail due to network, click 'Rerun Failed Queries' to retry only unsuccessful searches without exhausting quota.",
        "what_to_do_next": "Export longitudinal trends to Excel to include in client consulting reports or production planning presentations.",
        "export_and_saving": "Export differential comparison tables, historical run snapshots, and alert feeds to Excel (.xlsx).",
    },
    "saved_research": {
        "title": "💾 Saved Research & Project History",
        "category": "Storage & Offline Workspace",
        "summary": "Inspect historical keyword research sessions, review past query trees, and export archived projects.",
        "when_to_use": "Use to revisit earlier keyword crawls, reload historical data into current view, or clean up obsolete research runs.",
        "prerequisites": "At least one previously executed research crawl.",
        "steps": [
            "Navigate to '💾 Saved Research'.",
            "Browse past research runs sorted by date.",
            "Filter by seed keyword or research date.",
            "Click 'Inspect Session' to load keyword table and metrics.",
            "Export historical datasets to CSV or Excel.",
            "Delete obsolete sessions with safety confirmation.",
        ],
        "option_choices": {
            "Inspect vs Delete": "Inspecting loads full keyword records; Deleting safely purges session and cascade child records.",
        },
        "recommended_defaults": "Keep historical records intact to enable longitudinal analysis and topic overlap prevention.",
        "expected_result": "Instant offline access to past research without repeating network API calls.",
        "how_to_interpret": "Use past session dates to verify whether a keyword cluster was already researched recently.",
        "metric_explanations": {
            "Session Records": "Total unique keywords captured during that crawl session.",
            "Crawl Duration": "Time in seconds required to complete the query tree expansion.",
        },
        "interpreting_zero_results": "If no sessions appear, no keyword crawls have been completed yet. Launch a search from '🔍 New Keyword Research'.",
        "common_mistakes": "Deleting sessions that contain keywords you intended to target in future videos.",
        "troubleshooting": "If historical sessions are missing, check if a database restore was performed recently in Settings.",
        "what_to_do_next": "Compare past keywords against new autocomplete runs to identify emerging search trends.",
        "export_and_saving": "Archived sessions can be exported individually to CSV (UTF-8 BOM) or Excel.",
    },
    "studio_auth": {
        "title": "🔐 Studio Profile, Local Authentication & Vault",
        "category": "Account & Security",
        "summary": "Manage on-device creator identity, multi-workspace routing, API keys, and local SQLite cryptographic storage.",
        "when_to_use": "Use on first launch to configure your creator studio name, workspace mode, and verify your API credentials safely.",
        "prerequisites": "None. Works out of the box with default Local Studio settings.",
        "steps": [
            "Navigate to '🔐 Studio Profile & Auth'.",
            "Update your Studio / Creator Workspace Name.",
            "Select Workspace Mode: Solo Creator, Production Agency Workstation, Enterprise Research Suite, or Offline Privacy Vault.",
            "Set Default Geographic Target and Primary Niche focus.",
            "Click 'Save Studio Profile'.",
            "Switch to 'Local Vault & Privacy Diagnostics' tab to inspect SQLite WAL status, API key masking, and database health.",
        ],
        "option_choices": {
            "Workspace Modes": "Solo Creator (streamlined local workflow), Agency Workstation (multi-client reporting tags), Offline Vault (strict offline mode).",
        },
        "recommended_defaults": "Solo Creator mode with default region set to your primary YouTube audience geography.",
        "expected_result": "Persisted creator configuration stored safely in local SQLite with 0% external cloud telemetry.",
        "how_to_interpret": "All settings are saved locally in keywords.db; no account creation, passwords, or cloud syncing required.",
        "metric_explanations": {
            "WAL Mode": "Write-Ahead Logging enabled for atomic, zero-corruption SQLite concurrent operations.",
            "Key Masking": "Visual obfuscation of sensitive API keys to prevent accidental disclosure during streams.",
        },
        "interpreting_zero_results": "If diagnostic metrics fail to render, verify that SQLite write permissions exist in the application folder.",
        "common_mistakes": "Sharing screenshots containing unmasked API keys. Studio Profile always masks keys automatically.",
        "troubleshooting": "If profile changes do not appear, ensure write permissions exist in the application directory.",
        "what_to_do_next": "Navigate to '📊 Dashboard' to begin your research workflow.",
        "export_and_saving": "Profile configurations are committed immediately to the `app_settings` table in local SQLite.",
    },
    "settings_backup": {
        "title": "⚙️ Settings, Cache Management & SQLite Backups",
        "category": "Storage & Offline Workspace",
        "summary": "Inspect runtime environment, clear autocomplete cache, create verified online database backups, and restore with integrity checks.",
        "when_to_use": "Use periodically to backup your research database or clear cached queries to force fresh YouTube suggestions.",
        "prerequisites": "Local file system write access.",
        "steps": [
            "Navigate to '⚙️ Settings & Data Sources'.",
            "Inspect system runtime parameters, database size, and table row counts.",
            "Under 'Cache Maintenance', view cache hit ratio and cached queries count.",
            "Click 'Clear Expired Cache' or 'Purge All Cache' if fresh live suggestions are needed.",
            "Under 'Database Backups', click 'Create Verified Backup Now'.",
            "To restore, select an archived backup file from the list, review verified checksum, and confirm restore.",
        ],
        "option_choices": {
            "Clear Expired Cache": "Removes entries older than configured TTL (default 24h) while retaining fresh queries.",
            "Verified Online Backup": "Uses SQLite online backup API to produce consistent snapshots without locking the database.",
        },
        "recommended_defaults": "Create a database backup before performing major bulk research runs or system updates.",
        "expected_result": "A timestamped backup file in `data/backups/` verified via `PRAGMA integrity_check`.",
        "how_to_interpret": "Cache hit ratios above 40% indicate efficient local query reuse and zero redundant network latency.",
        "metric_explanations": {
            "Cache Hit Ratio": "Percentage of requests answered from local SQLite cache instead of external network calls.",
            "Integrity Check": "SQLite internal consistency verification confirming 0 database page corruption.",
        },
        "interpreting_zero_results": "Zero cached queries indicates a fresh installation or recent cache purge. New queries will populate cache automatically.",
        "common_mistakes": "Manually editing or deleting the `keywords.db` file while the Streamlit application is running.",
        "troubleshooting": "If database shows locked status, ensure no other background python processes have uncommitted transactions.",
        "what_to_do_next": "Return to Dashboard with confidence that your data is securely backed up.",
        "export_and_saving": "Verified snapshots are saved to `data/backups/` as standard portable SQLite databases.",
    },
}


# ==============================================================================
# 2. Interactive Guided Tours Framework (6 Major Sections)
# ==============================================================================

INTERACTIVE_TOURS: Dict[str, Dict[str, Any]] = {
    "keyword_studio": {
        "title": "Keyword Discovery Interactive Tour",
        "section_key": "keyword_discovery",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Primary Seed Keyword Input",
                "selector_ref": "Seed Input Field (top of research form)",
                "what_it_does": "Acts as the root search term from which YouTube's live autocomplete dropdown is queried.",
                "when_to_use": "Whenever you begin research on a new topic, niche, or product category.",
                "recommended_choice": "Enter a concise 2–3 word noun phrase (e.g. 'wireless earbuds' or 'python tutorial').",
                "what_happens_after": "Keyword Studio sends query requests to YouTube's live suggestion service.",
                "what_to_do_next": "Proceed to configure discovery depth and geographic region below.",
            },
            {
                "step_num": 2,
                "element_title": "Country, Language & Discovery Depth",
                "selector_ref": "Geographic Target & Depth Selector",
                "what_it_does": "Controls geographic market localization and whether suggestions are queried recursively.",
                "when_to_use": "Use to tailor results for your target audience geography and control crawl size.",
                "recommended_choice": "Default to Country US, Language English, Depth 2 for a balanced 80–120 keyword taxonomy.",
                "what_happens_after": "Recursive expansion discovers sub-branches that typical direct searches miss.",
                "what_to_do_next": "Choose your search mode: Direct, Recursive, or Pattern Variations.",
            },
            {
                "step_num": 3,
                "element_title": "Search Mode & Intent Pattern Variations",
                "selector_ref": "Search Mode Radio / Smart Variations Checkbox",
                "what_it_does": "Enables multi-angle modifier injection (best, vs, review, how to) to capture high-buyer queries.",
                "when_to_use": "Enable when researching commercial or affiliate niches where viewer buying intent matters.",
                "recommended_choice": "Check 'Smart Pattern Variations' to capture comparison and tutorial modifiers.",
                "what_happens_after": "Expands seed queries with intent-driven prefix and suffix variations.",
                "what_to_do_next": "Click 'Start Keyword Research' to begin query processing.",
            },
            {
                "step_num": 4,
                "element_title": "Discovered Keywords Table & Sanitized Export",
                "selector_ref": "Results Table & Export Buttons",
                "what_it_does": "Displays discovered keywords with linguistic intent, tail length, and provides CSV/Excel exports.",
                "when_to_use": "Inspect after crawl finishes to identify high-intent 4+ word long-tail opportunities.",
                "recommended_choice": "Filter by Long-tail queries with Commercial or Informational intent.",
                "what_happens_after": "Selected keywords can be saved to shortlist or sent to Competitor Video SERP research.",
                "what_to_do_next": "Navigate to '🎥 YouTube Video Research' to inspect competitor video view counts.",
            },
        ],
    },
    "video_serp": {
        "title": "Competitor SERP Intelligence Tour",
        "section_key": "video_serp",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Target Keyword Query Field",
                "selector_ref": "Video Search Query Input",
                "what_it_does": "Queries the top ranking videos currently appearing on YouTube search for this phrase.",
                "when_to_use": "Before producing any video, to verify the actual competition you will face in search.",
                "recommended_choice": "Select your highest-opportunity keyword discovered in the Autocomplete studio.",
                "what_happens_after": "Retrieves video titles, view counts, publish dates, channel subscribers, and tags.",
                "what_to_do_next": "Select your research date window to isolate recent vs evergreen competition.",
            },
            {
                "step_num": 2,
                "element_title": "Date Window & Provider Selection",
                "selector_ref": "Date Range Window Selectbox",
                "what_it_does": "Filters ranking videos by publication recency (Last 60 Days, 6 Months, All Time).",
                "when_to_use": "Use Last 60 Days to identify fresh trending momentum rather than 5-year-old viral outliers.",
                "recommended_choice": "Last 60 Days for fast-moving niches; All Time for foundational evergreen topics.",
                "what_happens_after": "Calculates median views and channel authority across videos published in that window.",
                "what_to_do_next": "Click 'Analyze YouTube SERP' to inspect competitor metrics.",
            },
            {
                "step_num": 3,
                "element_title": "Median View Count & Channel Authority Benchmark",
                "selector_ref": "SERP Metrics Cards",
                "what_it_does": "Displays median view count, small channel penetration, and upload distribution.",
                "when_to_use": "Use to judge whether a small creator can realistically rank on page 1.",
                "recommended_choice": "Look for keywords where median views are moderate (<15k) and small channels have ranked.",
                "what_happens_after": "Reveals whether the search term is a competitive red ocean or an open opportunity.",
                "what_to_do_next": "Inspect the Competitor Tag Cloud below to discover metadata patterns.",
            },
            {
                "step_num": 4,
                "element_title": "Competitor Tag Cloud & Search Gap Identification",
                "selector_ref": "Tag Cloud & SERP Gap Cards",
                "what_it_does": "Extracts the exact tags and keywords competitor channels tagged in their videos.",
                "when_to_use": "Use to discover overlooked video angles and borrow high-ranking tag concepts.",
                "recommended_choice": "Copy high-frequency competitor tags into your filming brief metadata.",
                "what_happens_after": "Prepares evidence-grounded inputs for your Content Brief and title hooks.",
                "what_to_do_next": "Navigate to '💡 Content Opportunities' to generate title hook variations.",
            },
        ],
    },
    "product_opportunities": {
        "title": "Niche Product Opportunity Finder Tour",
        "section_key": "product_opportunities",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Commercial Niche Name & Regional Scope",
                "selector_ref": "Niche Name Input (e.g. 'Mechanical Keyboards')",
                "what_it_does": "Sets the product market boundary and target language/country for commercial discovery.",
                "when_to_use": "When seeking physical products or software to review, sponsor, or create affiliate content for.",
                "recommended_choice": "Enter a specific product category (e.g. 'Wireless Earbuds', 'Coffee Grinders').",
                "what_happens_after": "The discovery engine maps brand entities and candidate product models.",
                "what_to_do_next": "Set query budget and minimum research coverage threshold.",
            },
            {
                "step_num": 2,
                "element_title": "Query Budget & Minimum Research Coverage",
                "selector_ref": "Query Budget & Coverage Slider",
                "what_it_does": "Specifies how many distinct search queries must be executed per product before classifying gaps.",
                "when_to_use": "Ensures that absence of videos is proven with real evidence rather than insufficient research.",
                "recommended_choice": "Set Min Coverage to at least 2 queries per product with a 40–60 query budget.",
                "what_happens_after": "Prevents false-absence claims by testing multiple naming conventions.",
                "what_to_do_next": "Click 'Start Niche Product Research' to execute discovery and 60-day gap scans.",
            },
            {
                "step_num": 3,
                "element_title": "60-Day Gap Classification & Distribution",
                "selector_ref": "Match Distribution Breakdown",
                "what_it_does": "Categorizes products into Zero Matches, Few Matches (1–3), Active Coverage, or Insufficient Research.",
                "when_to_use": "Use to isolate products with low creator coverage in the recent 60-day window.",
                "recommended_choice": "Focus on 'Zero Observed Matches' and 'Few Matches' with confirmed product identities.",
                "what_happens_after": "Filters the catalog down to high-potential content opportunities.",
                "what_to_do_next": "Inspect Evidence Cards to verify product specs and manufacturer details.",
            },
            {
                "step_num": 4,
                "element_title": "Evidence Cards & Shortlist Selection",
                "selector_ref": "Product Evidence Card & Add to Shortlist",
                "what_it_does": "Shows exact queries executed, matching videos retrieved, and research limitations disclosure.",
                "when_to_use": "Review before committing production time to verify product identity is authentic.",
                "recommended_choice": "Add verified high-score products to your Priority Shortlist.",
                "what_happens_after": "Shortlisted products are queued in '🏷️ Product Opportunity Planner' for affiliate briefs.",
                "what_to_do_next": "Navigate to '🏷️ Product Opportunity Planner' to formulate your monetization strategy.",
            },
        ],
    },
    "content_opportunities": {
        "title": "Content Opportunities & Hook Workshop Tour",
        "section_key": "content_opportunities",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Active Research Session Selector",
                "selector_ref": "Session Selectbox",
                "what_it_does": "Loads discovered keywords, competitor SERP metrics, and topic clusters from a past crawl.",
                "when_to_use": "Whenever you are ready to transition from raw keyword data to video production briefs.",
                "recommended_choice": "Select your most recent or comprehensive keyword crawl session.",
                "what_happens_after": "Renders topic clusters, opportunity scores, and hook workshop tools.",
                "what_to_do_next": "Use the Opportunity Score filter to isolate high-potential concepts.",
            },
            {
                "step_num": 2,
                "element_title": "Opportunity Score Filter (0–100)",
                "selector_ref": "Min Opportunity Score Slider",
                "what_it_does": "Filters topics using algorithmic score based on long-tail specificity and competitor weakness.",
                "when_to_use": "Use to cut through hundreds of keywords to the top 10% highest-converting opportunities.",
                "recommended_choice": "Set threshold to >= 65 to isolate strong opportunities with low competition.",
                "what_happens_after": "Hides crowded head terms and surfaces underserved creator gaps.",
                "what_to_do_next": "Inspect Semantic Topic Clusters to see related keywords.",
            },
            {
                "step_num": 3,
                "element_title": "Semantic Topic Clusters",
                "selector_ref": "Topic Cluster Accordion",
                "what_it_does": "Groups related long-tail keywords into unified video themes to prevent fragmented content.",
                "when_to_use": "Use to plan a single comprehensive video that ranks for 10+ related long-tail queries simultaneously.",
                "recommended_choice": "Target clusters with 4+ keywords and combined high search intent.",
                "what_happens_after": "Provides a unified content scope for your video outline.",
                "what_to_do_next": "Click 'Title Hook Workshop' to formulate high-CTR title variations.",
            },
            {
                "step_num": 4,
                "element_title": "Title Hook Workshop & Production Brief",
                "selector_ref": "Title Hook Cards & Brief Download",
                "what_it_does": "Generates 4 distinct title hook angles (Curiosity, Authority, Contrarian, Benefit) and filming brief.",
                "when_to_use": "When writing video titles, thumbnails, opening hooks, and structuring production talking points.",
                "recommended_choice": "Pair a Curiosity Hook title with a high-contrast visual thumbnail.",
                "what_happens_after": "Produces a production-ready brief with talking points, tags, and topic overlap checks.",
                "what_to_do_next": "Download the brief and begin scripting or filming your video.",
            },
        ],
    },
    "product_planner": {
        "title": "Product Opportunity Planner Tour",
        "section_key": "product_planner",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Niche Research Session Selector",
                "selector_ref": "Session Selectbox (top of planner)",
                "what_it_does": "Pulls verified product opportunities and 60-day gap metrics into your affiliate workspace.",
                "when_to_use": "To convert empirical product gaps into a prioritized commercial content calendar.",
                "recommended_choice": "Select your completed 60-day product gap research run.",
                "what_happens_after": "Populates verified products with opportunity scores and matching video counts.",
                "what_to_do_next": "Review and add products to your Priority Shortlist.",
            },
            {
                "step_num": 2,
                "element_title": "Priority Shortlist Queue",
                "selector_ref": "Shortlist Table & Priority Controls",
                "what_it_does": "Allows setting production priority (High, Medium, Low), target format, and creator notes.",
                "when_to_use": "Use to decide which physical review samples to purchase or contact brands for.",
                "recommended_choice": "Assign 'High' priority to verified products with 0 recent matching videos.",
                "what_happens_after": "Locks the product into your active filming pipeline with production tags.",
                "what_to_do_next": "Configure affiliate commission rates and revenue projections.",
            },
            {
                "step_num": 3,
                "element_title": "Affiliate Commission & ROI Calculator",
                "selector_ref": "Commission Rate & Retail Price Fields",
                "what_it_does": "Models estimated earnings per 10k views based on retail price, commission rate, and conversion rate.",
                "when_to_use": "Use to verify commercial upside before investing in filming expensive hardware reviews.",
                "recommended_choice": "Benchmark 4% for Amazon Associates or 10–15% for direct brand affiliate partnerships.",
                "what_happens_after": "Calculates projected earnings per 10k views and revenue potential.",
                "what_to_do_next": "Generate the Affiliate Content Brief with FTC Disclosure checklist.",
            },
            {
                "step_num": 4,
                "element_title": "Affiliate Content Brief & FTC Disclosure Checklist",
                "selector_ref": "Affiliate Brief Generator",
                "what_it_does": "Builds structured video outlines, comparison matrices, and compliant FTC affiliate disclosure copy.",
                "when_to_use": "Before filming or publishing to ensure compliance with advertising standards.",
                "recommended_choice": "Include spoken disclosure in the first 30 seconds and written disclosure in the top 3 lines of description.",
                "what_happens_after": "Provides a legally sound, high-converting video production blueprint.",
                "what_to_do_next": "Export the shortlist and brief to Excel or Notion for video production.",
            },
        ],
    },
    "research_monitor": {
        "title": "Automated Research Monitor Tour",
        "section_key": "research_monitor",
        "steps": [
            {
                "step_num": 1,
                "element_title": "Saved Research Configurations",
                "selector_ref": "Saved Configs Table & Selector",
                "what_it_does": "Stores reusable research recipes (Niche, Country, Window, Query Budget, Category Filters).",
                "when_to_use": "Use to maintain ongoing monitoring of key commercial niches without re-entering parameters.",
                "recommended_choice": "Create configurations for your core YouTube channel pillars.",
                "what_happens_after": "Enables repeatable on-demand scans and automated recurring schedules.",
                "what_to_do_next": "Configure scan frequency: Manual, Daily, Weekly, or Monthly.",
            },
            {
                "step_num": 2,
                "element_title": "On-Demand Run & In-Process Scheduler",
                "selector_ref": "Trigger Run Button & Schedule Controls",
                "what_it_does": "Executes repeatable scans locally and records point-in-time snapshots of the niche.",
                "when_to_use": "Run on-demand before starting a new video, or set weekly recurring monitoring.",
                "recommended_choice": "Weekly schedule with 40–50 query budget for optimal balance of coverage and speed.",
                "what_happens_after": "Produces unique timestamped run records with product discovery and video match logs.",
                "what_to_do_next": "Navigate to 'Snapshot Comparison' to inspect what changed since last scan.",
            },
            {
                "step_num": 3,
                "element_title": "Snapshot Differential Comparison",
                "selector_ref": "Run Comparison Selectors (Run A vs Run B)",
                "what_it_does": "Compares two points in time to detect newly released products, video count changes, and score shifts.",
                "when_to_use": "Use to detect if competitors have started covering your target product gap.",
                "recommended_choice": "Compare your latest run against the baseline run from 30 days ago.",
                "what_happens_after": "Highlights deltas (+ videos, - gap, new products) in high-contrast visual indicators.",
                "what_to_do_next": "Inspect the Change Alerts Feed for actionable notifications.",
            },
            {
                "step_num": 4,
                "element_title": "Change Alerts Feed & Longitudinal Trends",
                "selector_ref": "Change Alerts Feed & Trend Charts",
                "what_it_does": "Proactively alerts you when competitor video uploads surge or when a product gap widens.",
                "when_to_use": "Check weekly to catch newly emerging trends before the broader YouTube creator community.",
                "recommended_choice": "Act quickly when high-opportunity products maintain 0 matching videos across multiple runs.",
                "what_happens_after": "Gives you a persistent first-mover advantage in your niche.",
                "what_to_do_next": "Export historical snapshots to Excel for channel strategic planning.",
            },
        ],
    },
}


# ==============================================================================
# 3. Interactive Guided Tour Renderer
# ==============================================================================

def render_interactive_tour(tour_id: str) -> None:
    """Render an Apple-inspired interactive guided tour card for the current section.
    
    Provides Next, Back, Skip, and Finish controls, highlights target UI elements,
    and persists completion state in SQLite app_settings.
    """
    tour = INTERACTIVE_TOURS.get(tour_id)
    if not tour:
        return

    # Check persistence and session state
    is_completed = db_manager.get_setting(f"tour_completed_{tour_id}", "false") == "true"
    active_key = f"tour_{tour_id}_active"
    step_key = f"tour_{tour_id}_step"

    if active_key not in st.session_state:
        # Default to inactive if already completed, active on first encounter
        st.session_state[active_key] = not is_completed

    if not st.session_state[active_key]:
        return

    current_step = st.session_state.get(step_key, 0)
    steps = tour["steps"]
    total_steps = len(steps)

    # Clamp step index safely
    if current_step >= total_steps:
        current_step = total_steps - 1
        st.session_state[step_key] = current_step
    elif current_step < 0:
        current_step = 0
        st.session_state[step_key] = 0

    step_data = steps[current_step]

    # Render clean Apple-styled tour card
    st.markdown(
        f"""
        <div class="tour-callout-card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.65rem; flex-wrap: wrap; gap: 0.5rem;">
                <span class="status-badge" style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.75rem; font-weight: 700;">
                    📍 {tour['title']} &bull; Step {current_step + 1} of {total_steps}
                </span>
                <span style="font-size: 0.78rem; color: #64748B;">Target UI Reference: <code>{step_data['selector_ref']}</code></span>
            </div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 0.4rem;">
                {step_data['element_title']}
            </div>
            <div style="font-size: 0.88rem; color: #374151; line-height: 1.5; margin-bottom: 0.75rem;">
                {step_data['what_it_does']}
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.75rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.85rem; margin-bottom: 1rem; font-size: 0.82rem;">
                <div><b>When to use:</b> <span style="color: #4B5563;">{step_data['when_to_use']}</span></div>
                <div><b>Recommended choice:</b> <span style="color: #1D4ED8; font-weight: 600;">{step_data['recommended_choice']}</span></div>
                <div><b>What happens after:</b> <span style="color: #4B5563;">{step_data['what_happens_after']}</span></div>
                <div><b>What to do next:</b> <span style="color: #15803D; font-weight: 600;">{step_data['what_to_do_next']}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1.2, 1.5, 1])

    with btn_col1:
        if st.button("⬅️ Back", disabled=(current_step == 0), key=f"tour_btn_prev_{tour_id}", use_container_width=True):
            st.session_state[step_key] = max(0, current_step - 1)
            st.rerun()

    with btn_col2:
        if current_step < total_steps - 1:
            if st.button("Next ➡️", type="primary", key=f"tour_btn_next_{tour_id}", use_container_width=True):
                st.session_state[step_key] = current_step + 1
                st.rerun()
        else:
            if st.button("Finish Tour 🎉", type="primary", key=f"tour_btn_finish_{tour_id}", use_container_width=True):
                db_manager.set_setting(f"tour_completed_{tour_id}", "true")
                st.session_state[active_key] = False
                st.rerun()

    with btn_col3:
        st.caption(f"Progress: {int(((current_step + 1) / total_steps) * 100)}% complete")

    with btn_col4:
        if st.button("Skip Tour", key=f"tour_btn_skip_{tour_id}", use_container_width=True):
            db_manager.set_setting(f"tour_completed_{tour_id}", "true")
            st.session_state[active_key] = False
            st.rerun()


# ==============================================================================
# 4. Contextual Help Renderer (In-Page Expandable Drawer)
# ==============================================================================

def render_contextual_help(section_key: str) -> None:
    """Render an accessible contextual help drawer directly on the active page."""
    data = USER_GUIDE_SECTIONS.get(section_key)
    if not data:
        return

    tour_id_map = {
        "keyword_discovery": "keyword_studio",
        "video_serp": "video_serp",
        "product_opportunities": "product_opportunities",
        "content_opportunities": "content_opportunities",
        "product_planner": "product_planner",
        "research_monitor": "research_monitor",
    }
    associated_tour_id = tour_id_map.get(section_key)

    with st.expander(f"📖 Contextual Guide & Best Practices — {data['title']}", expanded=False):
        st.markdown(
            f"""
            <div class="guide-card">
                <div style="font-size: 0.95rem; color: #111827; font-weight: 600; margin-bottom: 0.4rem;">
                    {data['summary']}
                </div>
                <div style="font-size: 0.85rem; color: #4B5563; margin-bottom: 0.75rem;">
                    <b>When to use:</b> {data['when_to_use']} &bull; <b>Prerequisites:</b> {data['prerequisites']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_steps, col_advice = st.columns([1.3, 1])

        with col_steps:
            st.markdown("##### 📋 Step-by-Step Execution Guide")
            for idx, step in enumerate(data["steps"], 1):
                st.markdown(
                    f"""
                    <div class="guide-step-box">
                        <div class="guide-step-badge">{idx}</div>
                        <div style="font-size: 0.84rem; color: #374151; line-height: 1.5;">{step}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with col_advice:
            st.markdown("##### 💡 Recommended Choice & Rationale")
            st.markdown(
                f"""
                <div class="guide-callout-best">
                    <div style="font-weight: 700; color: #1D4ED8; font-size: 0.85rem; margin-bottom: 0.3rem;">
                        Recommended Default
                    </div>
                    <div style="font-size: 0.82rem; color: #1E293B; line-height: 1.45;">
                        {data['recommended_defaults']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("##### ⚠️ Common Pitfalls to Avoid")
            st.markdown(
                f"""
                <div style="font-size: 0.82rem; color: #B45309; background: rgba(180, 83, 9, 0.06); border: 1px solid rgba(180, 83, 9, 0.2); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
                    {data['common_mistakes']}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("##### 🚀 What to Do Next")
            st.markdown(
                f"""
                <div style="font-size: 0.82rem; color: #15803D; background: rgba(21, 128, 61, 0.06); border: 1px solid rgba(21, 128, 61, 0.2); border-radius: 8px; padding: 0.75rem;">
                    {data['what_to_do_next']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if associated_tour_id:
            st.markdown("---")
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.caption(f"Want interactive, on-screen element highlighting? Launch the {data['title']} tour.")
            with col_t2:
                if st.button("🔄 Restart Interactive Tour", key=f"guide_btn_restart_tour_{section_key}", use_container_width=True):
                    st.session_state[f"tour_{associated_tour_id}_active"] = True
                    st.session_state[f"tour_{associated_tour_id}_step"] = 0
                    db_manager.set_setting(f"tour_completed_{associated_tour_id}", "false")
                    st.rerun()


# ==============================================================================
# 5. First-Run Onboarding Engine (7 Distinct Creator Goals)
# ==============================================================================

ONBOARDING_GOALS: Dict[str, Dict[str, Any]] = {
    "keywords": {
        "title": "🔍 Find YouTube Keywords",
        "icon": "🔍",
        "description": "Expand seed queries into high-intent long-tail keywords using live autocomplete suggestions.",
        "target_page": "🔍 New Keyword Research",
        "workflow_key": "keywords",
        "badge": "Core Autocomplete",
        "steps": [
            "Enter a 2–3 word seed query in your niche",
            "Select Depth 2 recursive tree expansion",
            "Filter long-tail queries and buyer search intent",
            "Inspect competitor SERP view metrics and tags",
            "Export sanitized keyword shortlist to CSV/XLSX",
        ],
    },
    "niche": {
        "title": "🌐 Research a Whole Niche",
        "icon": "🌐",
        "description": "Map broad niche demand, discover physical & digital products, and benchmark channel saturation.",
        "target_page": "📦 Niche Product Opportunity Finder",
        "workflow_key": "niche_products",
        "badge": "Market Intelligence",
        "steps": [
            "Define target niche category and geographic market",
            "Run automated product discovery queries",
            "Verify product identities and brand specifications",
            "Inspect recent 60-day YouTube video coverage",
            "Filter high-opportunity candidates into planner",
        ],
    },
    "product_gaps": {
        "title": "📦 60-Day Product Search Gaps",
        "icon": "📦",
        "description": "Discover real commercial products with few or zero matching YouTube videos in the last 60 days.",
        "target_page": "📦 Niche Product Opportunity Finder",
        "workflow_key": "niche_products",
        "badge": "Untapped Demand",
        "steps": [
            "Input commercial niche (e.g. 'Wireless Earbuds', 'Keyboards')",
            "Set date window to Last 60 Days with Min Coverage = 2",
            "Isolate 'Zero Observed Matches' and 'Few Matches' products",
            "Review query evidence logs and audit notes",
            "Shortlist products with confirmed commercial intent",
        ],
    },
    "competitor_serp": {
        "title": "🎥 Analyze Competitor Videos",
        "icon": "🎥",
        "description": "Inspect top-ranking YouTube videos, median view counts, channel authority, and hidden tags.",
        "target_page": "🎥 YouTube Video Research",
        "workflow_key": "competitors",
        "badge": "SERP Intelligence",
        "steps": [
            "Enter candidate keyword or competitor seed query",
            "Fetch top 10–20 ranking videos and upload recency",
            "Inspect median view count and subscriber authority",
            "Extract competitor video tags and keyword clusters",
            "Identify content gaps where top videos are weak or outdated",
        ],
    },
    "video_topics": {
        "title": "💡 Choose Video Topics",
        "icon": "💡",
        "description": "Cluster search terms into cohesive video concepts and generate curiosity-driven title hooks.",
        "target_page": "💡 Content Opportunities",
        "workflow_key": "keywords",
        "badge": "Hook Workshop",
        "steps": [
            "Select active keyword research session",
            "Review semantic topic clusters and opportunity scores",
            "Launch Title Hook Workshop for high-scoring concepts",
            "Select from 4 hook archetypes (Curiosity, Authority, etc.)",
            "Run channel overlap check to prevent self-cannibalization",
        ],
    },
    "content_brief": {
        "title": "📝 Create a Content Brief",
        "icon": "📝",
        "description": "Build structured filming briefs with target tags, competitor benchmarks, and title variations.",
        "target_page": "💡 Content Opportunities",
        "workflow_key": "keywords",
        "badge": "Production Ready",
        "steps": [
            "Select prioritized content opportunity",
            "Generate talking points and video structure outline",
            "Incorporate competitor benchmark metrics and tags",
            "Include affiliate disclosure compliance notes if applicable",
            "Export complete content brief in markdown or text",
        ],
    },
    "export_reports": {
        "title": "📤 Export Research Reports",
        "icon": "📤",
        "description": "Download formula-sanitized CSV and Excel datasets with formula injection protection.",
        "target_page": "💾 Saved Research",
        "workflow_key": "keywords",
        "badge": "Safe Data Export",
        "steps": [
            "Inspect active session or historical research run",
            "Filter keywords or products by desired criteria",
            "Select export format: UTF-8 BOM CSV or Excel (.xlsx)",
            "Verify automatic formula sanitization (=, +, -, @)",
            "Save production-ready file to your local computer",
        ],
    },
}


def render_onboarding_guide(is_ready: bool) -> None:
    """Render an optional 7-goal onboarding card if the user has not dismissed it."""
    if not is_ready:
        return

    # Check if user has previously dismissed onboarding
    has_onboarded = db_manager.get_setting("user_onboarded_v17", "false") == "true"
    if has_onboarded or st.session_state.get("dismiss_onboarding_temp", False):
        return

    st.markdown(
        """
        <div class="showcase-card animate-fade-in" style="border: 2px solid #2563EB; background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%); margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                <span class="hero-eyebrow" style="margin-bottom: 0;">🚀 WELCOME TO KEYWORD STUDIO</span>
                <span style="font-size: 0.78rem; color: #64748B;">Quick Onboarding & Objective Selection</span>
            </div>
            <h3 style="margin: 0.5rem 0 0.25rem 0; font-size: 1.35rem; font-weight: 800; color: #111827;">
                What do you want to accomplish today?
            </h3>
            <p style="margin: 0 0 1.25rem 0; font-size: 0.88rem; color: #4B5563;">
                Select an objective to launch a tailored workflow plan with recommended default settings.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render 7 distinct goals: Row 1 (4 goals), Row 2 (3 goals)
    goals_list = list(ONBOARDING_GOALS.items())
    row1 = goals_list[:4]
    row2 = goals_list[4:]

    cols_row1 = st.columns(4)
    for idx, (goal_key, goal_data) in enumerate(row1):
        with cols_row1[idx]:
            st.markdown(
                f"""
                <div class="goal-card">
                    <div>
                        <span class="status-badge" style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.72rem; font-weight: 700; margin-bottom: 0.4rem; display: inline-block;">
                            {goal_data['badge']}
                        </span>
                        <div style="font-weight: 700; color: #111827; font-size: 0.92rem; margin-bottom: 0.35rem;">
                            {goal_data['title']}
                        </div>
                        <div style="font-size: 0.78rem; color: #64748B; line-height: 1.4; margin-bottom: 0.75rem;">
                            {goal_data['description']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Start Workflow →", key=f"ob_goal_btn_{goal_key}", use_container_width=True):
                db_manager.set_setting("selected_onboarding_goal", goal_key)
                db_manager.set_setting("user_onboarded_v17", "true")
                st.session_state.active_workflow_goal = goal_data["workflow_key"]
                st.session_state.current_page = goal_data["target_page"]
                st.rerun()

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    cols_row2 = st.columns(3)
    for idx, (goal_key, goal_data) in enumerate(row2):
        with cols_row2[idx]:
            st.markdown(
                f"""
                <div class="goal-card">
                    <div>
                        <span class="status-badge" style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.72rem; font-weight: 700; margin-bottom: 0.4rem; display: inline-block;">
                            {goal_data['badge']}
                        </span>
                        <div style="font-weight: 700; color: #111827; font-size: 0.92rem; margin-bottom: 0.35rem;">
                            {goal_data['title']}
                        </div>
                        <div style="font-size: 0.78rem; color: #64748B; line-height: 1.4; margin-bottom: 0.75rem;">
                            {goal_data['description']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Start Workflow →", key=f"ob_goal_btn_{goal_key}", use_container_width=True):
                db_manager.set_setting("selected_onboarding_goal", goal_key)
                db_manager.set_setting("user_onboarded_v17", "true")
                st.session_state.active_workflow_goal = goal_data["workflow_key"]
                st.session_state.current_page = goal_data["target_page"]
                st.rerun()

    # Skip / Dismiss Row
    col_skip1, col_skip2 = st.columns([4, 1.2])
    with col_skip1:
        st.caption("You can reopen this onboarding guide or change your active goal anytime in Settings or the User Guide.")
    with col_skip2:
        if st.button("Skip / Don't Show Again", use_container_width=True, key="ob_btn_dismiss"):
            db_manager.set_setting("user_onboarded_v17", "true")
            st.session_state.dismiss_onboarding_temp = True
            st.rerun()
    st.markdown("---")


# ==============================================================================
# 6. Smart Workflow Plans & Progress Tracking (Evaluated from Real Conditions)
# ==============================================================================

WORKFLOW_PLANS: Dict[str, Dict[str, Any]] = {
    "keywords": {
        "title": "Keyword Research Workflow (7 Steps)",
        "summary": "End-to-end keyword taxonomy mapping from seed entry to verified long-tail shortlist export.",
        "steps": [
            {
                "id": "kw_seed",
                "title": "Enter Seed Keyword",
                "description": "Provide a clean 2–3 word topic or niche phrase.",
                "prerequisites": "None. Free-first operation with zero credentials.",
                "recommended_defaults": "2–3 words noun phrase (e.g. 'wireless earbuds').",
                "expected_output": "Initial root query ready for tree expansion.",
                "common_mistakes": "Using long conversational questions as root queries.",
                "target_page": "🔍 New Keyword Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "last_query", "") or (db.get_recent_searches(1) if ready else [])),
            },
            {
                "id": "kw_expand",
                "title": "Run Autocomplete Crawl",
                "description": "Execute live autocomplete suggestions with Depth 2 recursive tree mapping.",
                "prerequisites": "Seed keyword entered.",
                "recommended_defaults": "Recursive Depth 2, Target US/en, Smart Patterns enabled.",
                "expected_output": "80–120 unique keywords retrieved with query paths.",
                "common_mistakes": "Stopping after single-depth query.",
                "target_page": "🔍 New Keyword Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "direct_results", []) or (getattr(s, "crawl_result", None) and getattr(s.crawl_result, "keywords", []))),
            },
            {
                "id": "kw_intent",
                "title": "Filter by Intent & Tail Length",
                "description": "Isolate high-intent 4+ word Long-tail and Commercial/Transactional keywords.",
                "prerequisites": "Keywords discovered in active session.",
                "recommended_defaults": "Tail Length: Long-tail, Intent: Commercial or Transactional.",
                "expected_output": "Filtered high-converting keyword candidate list.",
                "common_mistakes": "Focusing only on high-competition 1-word head terms.",
                "target_page": "📊 Research Results",
                "evaluator": lambda s, db, ready: bool(
                    getattr(s, "filtered_results_inspected", False)
                    or (getattr(s, "crawl_result", None) and any(k.tail_length == "Long-tail" for k in s.crawl_result.keywords))
                ),
            },
            {
                "id": "kw_serp",
                "title": "Inspect Competitor Video SERP",
                "description": "Examine top-ranking videos, view counts, and subscriber authority.",
                "prerequisites": "Candidate keyword selected.",
                "recommended_defaults": "Date window: Last 60 Days to verify fresh competition.",
                "expected_output": "Benchmark of competitor views, channel size, and video tags.",
                "common_mistakes": "Assuming high autocomplete frequency guarantees easy ranking without checking SERP.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "current_serp_analysis", None) is not None),
            },
            {
                "id": "kw_score",
                "title": "Evaluate Opportunity Score",
                "description": "Review transparent 0–100 heuristic opportunity score and content gaps.",
                "prerequisites": "SERP metrics collected.",
                "recommended_defaults": "Target opportunity scores >= 65.",
                "expected_output": "Prioritized list of viable video concepts.",
                "common_mistakes": "Relying on vanity view counts rather than search gap vulnerability.",
                "target_page": "💡 Content Opportunities",
                "evaluator": lambda s, db, ready: bool(getattr(s, "scored_opportunities", []) or (getattr(s, "current_serp_analysis", None) is not None)),
            },
            {
                "id": "kw_cluster",
                "title": "Cluster Related Long-Tails",
                "description": "Group semantic keyword variations into cohesive video concepts.",
                "prerequisites": ">= 5 discovered keywords.",
                "recommended_defaults": "Group 3–6 related long-tail keywords per video topic.",
                "expected_output": "Topic clusters that allow one video to rank for multiple terms.",
                "common_mistakes": "Filming separate thin videos for near-duplicate keywords.",
                "target_page": "💡 Content Opportunities",
                "evaluator": lambda s, db, ready: bool(getattr(s, "topic_clusters", []) or getattr(s, "active_clusters_generated", False)),
            },
            {
                "id": "kw_export",
                "title": "Export Sanitized Keyword Dataset",
                "description": "Download formula-safe CSV (UTF-8 BOM) or Excel (.xlsx) files.",
                "prerequisites": "Clustered or filtered keywords.",
                "recommended_defaults": "CSV UTF-8 BOM or Excel (.xlsx) with formula sanitization enabled.",
                "expected_output": "Clean spreadsheet ready for production Notion/Obsidian calendars.",
                "common_mistakes": "Opening unquoted CSVs directly without UTF-8 BOM support.",
                "target_page": "📊 Research Results",
                "evaluator": lambda s, db, ready: bool(getattr(s, "last_exported_file", "") or getattr(s, "export_completed", False)),
            },
        ],
    },
    "niche_products": {
        "title": "Niche Product Research Workflow (9 Steps)",
        "summary": "Discover real commercial products, verify model specifications, and check 60-day YouTube upload gaps.",
        "steps": [
            {
                "id": "prod_niche",
                "title": "Define Niche Scope & Geography",
                "description": "Specify target commercial niche and market language/country.",
                "prerequisites": "Commercial product interest.",
                "recommended_defaults": "Specific niche (e.g. 'Espresso Machines'), Country US, Language English.",
                "expected_output": "Configured niche workspace ready for automated discovery.",
                "common_mistakes": "Setting overly broad categories like 'Electronics'.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "active_niche_name", "")),
            },
            {
                "id": "prod_discovery",
                "title": "Execute Product Discovery Queries",
                "description": "Run curated catalog, autocomplete entity, or smart angle discovery.",
                "prerequisites": "Niche name defined.",
                "recommended_defaults": "Curated catalog mode with 30–50 query budget.",
                "expected_output": "Raw candidate product entities extracted.",
                "common_mistakes": "Using insufficient query budget leading to low coverage.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "discovered_products_count", 0) > 0 or getattr(s, "discovered_products", [])),
            },
            {
                "id": "prod_extract",
                "title": "Extract Candidate Product Entities",
                "description": "Isolate brand name, model number, and primary product specifications.",
                "prerequisites": "Discovery queries executed.",
                "recommended_defaults": "Extract distinct model variations.",
                "expected_output": "Structured list of potential physical or digital products.",
                "common_mistakes": "Treating generic adjectives as brand names.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "extracted_candidates_count", 0) > 0 or getattr(s, "discovered_products", [])),
            },
            {
                "id": "prod_verify",
                "title": "Verify Product Identity & Details",
                "description": "Confirm manufacturer model number and real-world commercial validity.",
                "prerequisites": "Candidate products extracted.",
                "recommended_defaults": "Require manufacturer verification before high-budget video planning.",
                "expected_output": "Verified product catalog with reliable entity identities.",
                "common_mistakes": "Assuming unverified AI entities exist in the real market.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "verified_products_count", 0) > 0),
            },
            {
                "id": "prod_gap",
                "title": "Execute 60-Day YouTube Gap Check",
                "description": "Search YouTube for recent matching videos within the last 60 days.",
                "prerequisites": "Verified products catalog.",
                "recommended_defaults": "Last 60 Days, Min Coverage = 2 queries per product.",
                "expected_output": "Empirical counts of observed matching videos per product.",
                "common_mistakes": "Concluding zero videos platform-wide from a single failed query.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "gap_check_completed", False) or getattr(s, "product_gap_results", [])),
            },
            {
                "id": "prod_score",
                "title": "Calculate 0–100 Opportunity Score",
                "description": "Run transparent heuristic opportunity scoring separate from confidence.",
                "prerequisites": "60-day gap check completed.",
                "recommended_defaults": "Target opportunity scores >= 70 with High research confidence.",
                "expected_output": "Ranked opportunity scores reflecting gap size and search evidence.",
                "common_mistakes": "Awarding high scores to products with zero research coverage.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "scored_products_count", 0) > 0),
            },
            {
                "id": "prod_filter",
                "title": "Filter Weak & Low-Evidence Items",
                "description": "Purge products marked 'Insufficient Research' or unverified identity.",
                "prerequisites": "Opportunity scores calculated.",
                "recommended_defaults": "Filter out items with < 2 executed verification queries.",
                "expected_output": "High-confidence shortlist of genuine creator opportunities.",
                "common_mistakes": "Including unverified items in production schedules.",
                "target_page": "📦 Niche Product Opportunity Finder",
                "evaluator": lambda s, db, ready: bool(getattr(s, "filtered_products_count", 0) > 0),
            },
            {
                "id": "prod_serp_review",
                "title": "Review Observed Competitor Videos",
                "description": "Inspect retrieved competitor video titles to confirm matching angle.",
                "prerequisites": "Filtered product candidates.",
                "recommended_defaults": "Verify whether existing videos are superficial unboxings or in-depth reviews.",
                "expected_output": "Clear understanding of competitor depth on each product.",
                "common_mistakes": "Assuming a video with the same brand name is an exact model match.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "current_serp_analysis", None) is not None),
            },
            {
                "id": "prod_planner_save",
                "title": "Save Top Opportunities to Planner",
                "description": "Add prioritized candidates into Affiliate Content Planner with notes.",
                "prerequisites": "Reviewed product candidates.",
                "recommended_defaults": "Assign High priority to verified products with 0 recent videos.",
                "expected_output": "Persisted affiliate content shortlist ready for production briefs.",
                "common_mistakes": "Leaving research in temporary view without saving to planner.",
                "target_page": "🏷️ Product Opportunity Planner",
                "evaluator": lambda s, db, ready: bool(getattr(s, "planner_shortlist_count", 0) > 0),
            },
        ],
    },
    "competitors": {
        "title": "Competitor Research Workflow (6 Steps)",
        "summary": "Benchmark competitor authority, extract metadata tags, and identify underserved video angles.",
        "steps": [
            {
                "id": "comp_seed",
                "title": "Identify Competitor Seed Query",
                "description": "Select competitor channel name or high-ranking target query.",
                "prerequisites": "Target niche established.",
                "recommended_defaults": "Core competitive topic (e.g. 'notion for students').",
                "expected_output": "Seed query targeting competitor rankings.",
                "common_mistakes": "Focusing on head terms dominated by multi-million subscriber channels.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "last_query", "")),
            },
            {
                "id": "comp_fetch",
                "title": "Fetch YouTube SERP Ranking Videos",
                "description": "Retrieve top 10–20 ranking videos with live metadata from YouTube API.",
                "prerequisites": "Competitor query entered.",
                "recommended_defaults": "Date window: Last 60 Days to observe active creator competition.",
                "expected_output": "Ranked video list with view counts, likes, and channels.",
                "common_mistakes": "Judging competition purely from subscriber counts.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "current_serp_analysis", None) is not None),
            },
            {
                "id": "comp_metrics",
                "title": "Inspect Views & Subscriber Ratios",
                "description": "Evaluate median views and identify small channels punching above their weight.",
                "prerequisites": "SERP videos fetched.",
                "recommended_defaults": "Look for videos with view-to-sub ratios > 3.0x indicating high search pull.",
                "expected_output": "Identified outlier videos that prove audience appetite.",
                "common_mistakes": "Ignoring high-performing videos from smaller channels.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "current_serp_analysis", None) and getattr(s.current_serp_analysis, "videos", [])),
            },
            {
                "id": "comp_gaps",
                "title": "Identify Vulnerable Angles & Gaps",
                "description": "Find queries where top ranking videos are >1 year old or have low retention hooks.",
                "prerequisites": "Competitor metrics analyzed.",
                "recommended_defaults": "Target topics where existing videos have outdated software versions or poor audio.",
                "expected_output": "Validated editorial angle to surpass existing top videos.",
                "common_mistakes": "Copying competitor video structure without a distinct value proposition.",
                "target_page": "💡 Content Opportunities",
                "evaluator": lambda s, db, ready: bool(getattr(s, "scored_opportunities", []) or getattr(s, "topic_clusters", [])),
            },
            {
                "id": "comp_tags",
                "title": "Extract Competitor Tags & Patterns",
                "description": "Analyze competitor tag cloud to uncover hidden keywords and modifier patterns.",
                "prerequisites": "SERP video metadata loaded.",
                "recommended_defaults": "Extract top 10 most frequent tags among ranking videos.",
                "expected_output": "High-intent tag list ready for your upload metadata.",
                "common_mistakes": "Using irrelevant viral tags that reduce metadata authority.",
                "target_page": "🎥 YouTube Video Research",
                "evaluator": lambda s, db, ready: bool(getattr(s, "current_serp_analysis", None) and getattr(s.current_serp_analysis, "extracted_tags", [])),
            },
            {
                "id": "comp_brief",
                "title": "Generate Gap-Targeting Content Brief",
                "description": "Build filming brief with title hooks specifically designed to beat competitors.",
                "prerequisites": "Identified gaps and extracted tags.",
                "recommended_defaults": "Use Contrarian or Authority hook archetypes to challenge incumbent videos.",
                "expected_output": "Comprehensive filming brief ready for scriptwriting.",
                "common_mistakes": "Filming without pre-validating title hook strength.",
                "target_page": "💡 Content Opportunities",
                "evaluator": lambda s, db, ready: bool(getattr(s, "active_brief_shortlist_id", None) or getattr(s, "content_brief_ready", False)),
            },
        ],
    },
}


def render_workflow_progress_checklist(workflow_key: Optional[str] = None, is_ready: bool = True) -> None:
    """Render an Apple-style workflow progress checklist evaluated strictly from actual data conditions."""
    if not workflow_key:
        workflow_key = st.session_state.get("active_workflow_goal", "keywords")
        if workflow_key not in WORKFLOW_PLANS:
            workflow_key = "keywords"

    plan = WORKFLOW_PLANS.get(workflow_key, WORKFLOW_PLANS["keywords"])
    steps = plan["steps"]
    total_steps = len(steps)

    # Evaluate real conditions for each step
    step_results = []
    completed_count = 0
    first_incomplete_idx = -1

    for idx, step in enumerate(steps):
        try:
            is_done = step["evaluator"](st.session_state, db_manager, is_ready)
        except Exception:
            is_done = False

        if is_done:
            completed_count += 1
        elif first_incomplete_idx == -1:
            first_incomplete_idx = idx

        step_results.append((step, is_done))

    percent_complete = int((completed_count / total_steps) * 100) if total_steps > 0 else 0

    st.markdown(
        f"""
        <div class="workflow-checklist-container">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <span class="status-badge" style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.75rem; font-weight: 700;">
                        📋 ACTIVE WORKFLOW PLAN
                    </span>
                    <h4 style="margin: 0.35rem 0 0.15rem 0; color: #111827; font-size: 1.1rem; font-weight: 800;">
                        {plan['title']}
                    </h4>
                    <div style="font-size: 0.82rem; color: #64748B;">
                        {plan['summary']}
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 1.15rem; font-weight: 800; color: #2563EB;">{completed_count} / {total_steps}</span>
                    <span style="font-size: 0.8rem; color: #64748B;"> ({percent_complete}%)</span>
                </div>
            </div>
            <div class="checklist-progress-bg">
                <div class="checklist-progress-fill" style="width: {percent_complete}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"🔍 Detailed Workflow Checklist ({completed_count}/{total_steps} Steps Verified)", expanded=False):
        for idx, (step, is_done) in enumerate(step_results, 1):
            is_current = (idx - 1) == first_incomplete_idx
            status_badge = (
                "<span style='color: #15803D; font-weight: 700;'>✅ Complete</span>"
                if is_done
                else ("<span style='color: #2563EB; font-weight: 700;'>⚡ Current Next Step</span>" if is_current else "<span style='color: #94A3B8;'>⏳ Pending</span>")
            )

            col_item1, col_item2 = st.columns([3, 1])
            with col_item1:
                st.markdown(
                    f"""
                    <div style="padding: 0.4rem 0;">
                        <b>Step {idx}: {step['title']}</b> &bull; {status_badge}<br/>
                        <span style="font-size: 0.82rem; color: #4B5563;">{step['description']}</span><br/>
                        <span style="font-size: 0.78rem; color: #64748B;"><b>Prereq:</b> {step['prerequisites']} | <b>Recommended:</b> {step['recommended_defaults']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_item2:
                if not is_done:
                    if st.button("Go to Step →", key=f"btn_wf_goto_{step['id']}", use_container_width=True):
                        st.session_state.current_page = step["target_page"]
                        st.rerun()


# ==============================================================================
# 7. Deterministic Next-Best-Action Guidance Engine
# ==============================================================================

@dataclass
class GuidanceRecommendation:
    """Structured deterministic recommendation based on real application state."""
    action_title: str
    action_description: str
    why_recommended: str
    prerequisites_met: str
    expected_outcome: str
    target_page: str
    button_label: str
    urgency: str = "normal"  # normal, high, completed


class DeterministicGuidanceEngine:
    """Evaluates actual session state and database history to recommend the optimal next action."""

    @staticmethod
    def evaluate_state(session_state: Any, is_ready: bool) -> GuidanceRecommendation:
        """Inspect actual application state and return the next best action."""
        last_query = getattr(session_state, "last_query", "") or ""
        direct_results = getattr(session_state, "direct_results", []) or []
        crawl_result = getattr(session_state, "crawl_result", None)
        current_serp = getattr(session_state, "current_serp_analysis", None)
        raw_quota = getattr(session_state, "provider_quota_exhausted", False)
        quota_exhausted = (raw_quota is True)

        raw_unverified = getattr(session_state, "unverified_products_count", 0)
        unverified_count = raw_unverified if (isinstance(raw_unverified, int) and not isinstance(raw_unverified, bool)) else 0

        raw_coverage = getattr(session_state, "research_coverage_pct", 100)
        coverage_pct = raw_coverage if (isinstance(raw_coverage, (int, float)) and not isinstance(raw_coverage, bool)) else 100

        raw_planner = getattr(session_state, "planner_shortlist_count", 0)
        planner_shortlist = raw_planner if (isinstance(raw_planner, int) and not isinstance(raw_planner, bool)) else 0

        # Rule 1: No query searched yet
        if not last_query and not direct_results and not crawl_result:
            return GuidanceRecommendation(
                action_title="Enter a Seed Keyword to Begin Research",
                action_description="Start by typing a broad niche or product term (e.g. 'wireless earbuds' or 'python tutorial').",
                why_recommended="YouTube's suggestion API requires a seed phrase to discover authentic audience search queries.",
                prerequisites_met="Ready. No credentials required.",
                expected_outcome="Instant collection of 10–100+ real search queries with intent classification.",
                target_page="🔍 New Keyword Research",
                button_label="🚀 Start Keyword Research",
                urgency="high",
            )

        # Rule 2: API quota exhaustion or provider error (strictly verified boolean)
        if quota_exhausted is True:
            return GuidanceRecommendation(
                action_title="Switch to Public Scraper Fallback or Refresh API Key",
                action_description="Your YouTube Data API quota has reached its daily limit. Switch to public scraper mode or update your key.",
                why_recommended="Maintains uninterrupted research without waiting for midnight quota replenishment.",
                prerequisites_met="Public scraper fallback is operational.",
                expected_outcome="Continued competitor SERP and autocomplete queries without API quota consumption.",
                target_page="⚙️ Settings & Data Sources",
                button_label="⚙️ Review API Settings",
                urgency="high",
            )

        # Rule 3: Keywords collected, but no video SERP analysis conducted
        total_keywords = len(direct_results) if direct_results else (len(crawl_result.keywords) if crawl_result else 0)
        if total_keywords > 0 and current_serp is None:
            top_kw = direct_results[0].keyword if direct_results else (crawl_result.keywords[0].keyword if crawl_result and crawl_result.keywords else "your top keyword")
            return GuidanceRecommendation(
                action_title=f"Inspect YouTube SERP for '{top_kw}'",
                action_description="Analyze existing competitor rankings, median view counts, and video tags for your highest-ranking keyword.",
                why_recommended="Keywords without competitor analysis risk competing against entrenched videos with millions of views.",
                prerequisites_met=f"Completed: {total_keywords} keywords discovered.",
                expected_outcome="Clear benchmark of competitor subscriber authority, view distribution, and keyword tags.",
                target_page="🎥 YouTube Video Research",
                button_label="🎥 Inspect Video SERP",
                urgency="high",
            )

        # Rule 4: Products discovered but unverified identities
        if unverified_count > 0:
            return GuidanceRecommendation(
                action_title="Verify Extracted Product Identities",
                action_description=f"You have {unverified_count} discovered product entities pending manufacturer identity verification.",
                why_recommended="Unverified products risk generating content briefs for discontinued or fictitious model numbers.",
                prerequisites_met="Discovered candidates extracted from search queries.",
                expected_outcome="Verified model specifications and high confidence for your affiliate production brief.",
                target_page="📦 Niche Product Opportunity Finder",
                button_label="📦 Verify Product Identities",
                urgency="high",
            )

        # Rule 5: Low research coverage (< 30%)
        if coverage_pct < 30:
            return GuidanceRecommendation(
                action_title="Expand Query Budget to Improve Coverage",
                action_description=f"Current research coverage is {coverage_pct}%. Increase the query budget to prevent false gap conclusions.",
                why_recommended="At least 2 distinct queries per product are required to prove low video coverage reliably.",
                prerequisites_met="Preliminary scan executed.",
                expected_outcome="High-confidence gap evidence ready for affiliate video production.",
                target_page="📦 Niche Product Opportunity Finder",
                button_label="📦 Expand Query Coverage",
                urgency="normal",
            )

        # Rule 6: Shortlist ready in planner -> Configure affiliate rates & briefs
        if planner_shortlist > 0:
            return GuidanceRecommendation(
                action_title="Configure Affiliate Rates & Generate Production Briefs",
                action_description=f"You have {planner_shortlist} shortlisted products ready for monetization modeling and FTC briefs.",
                why_recommended="Transforms research candidates into actionable filming plans with projected affiliate ROI.",
                prerequisites_met=f"Shortlisted: {planner_shortlist} verified products.",
                expected_outcome="Complete filming brief with hook archetypes, talking points, and FTC compliance text.",
                target_page="🏷️ Product Opportunity Planner",
                button_label="🏷️ Open Affiliate Planner",
                urgency="normal",
            )

        # Rule 7: SERP analysis completed, recommend Content Brief generation
        if current_serp is not None:
            return GuidanceRecommendation(
                action_title="Generate a Standout Title & Content Brief",
                action_description="Craft curiosity-driven title hooks and build a comprehensive filming brief in Content Opportunities.",
                why_recommended="Transform competitor intelligence into an actionable filming plan with pre-validated title hooks.",
                prerequisites_met=f"Completed: SERP analyzed for '{current_serp.query}'.",
                expected_outcome="Production-ready brief with 4 distinct title hook angles, video tags, and overlap checks.",
                target_page="💡 Content Opportunities",
                button_label="💡 Build Content Brief",
                urgency="normal",
            )

        # Rule 8: General fallback
        return GuidanceRecommendation(
            action_title="Discover Untapped 60-Day Product Gaps",
            action_description="Scan commercial products in your niche to identify candidates with zero or few observed videos in the last 60 days.",
            why_recommended="Commercial product reviews with low competition offer the highest affiliate revenue and CPM.",
            prerequisites_met="All systems operational.",
            expected_outcome="Verified list of products with observed upload counts and affiliate monetization potential.",
            target_page="📦 Niche Product Opportunity Finder",
            button_label="📦 Explore Product Gaps",
            urgency="normal",
        )


def render_next_best_action_banner(is_ready: bool) -> None:
    """Render the Apple-style Next-Best-Action guidance card."""
    rec = DeterministicGuidanceEngine.evaluate_state(st.session_state, is_ready)

    urgency_border = "#2563EB" if rec.urgency == "high" else "#6366F1"
    badge_text = "RECOMMENDED NEXT STEP" if rec.urgency == "high" else "SMART WORKFLOW SUGGESTION"

    st.markdown(
        f"""
        <div class="workflow-assistant-card" style="border-left: 4px solid {urgency_border};">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                <span class="status-badge" style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.75rem; font-weight: 700;">
                    ⚡ {badge_text}
                </span>
                <span style="font-size: 0.78rem; color: #64748B;">Based on your current studio session</span>
            </div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #111827; margin-bottom: 0.35rem;">
                {rec.action_title}
            </div>
            <div style="font-size: 0.86rem; color: #4B5563; line-height: 1.5; margin-bottom: 0.75rem;">
                {rec.action_description}
            </div>
            <div style="display: flex; gap: 1.5rem; font-size: 0.78rem; color: #64748B; flex-wrap: wrap;">
                <div><b>Why:</b> {rec.why_recommended}</div>
                <div><b>Outcome:</b> {rec.expected_outcome}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(f"{rec.button_label} →", type="primary", use_container_width=True, key="btn_next_best_action"):
        st.session_state.current_page = rec.target_page
        st.rerun()


# ==============================================================================
# 8. Guidance & Tour Preferences Reset Helper
# ==============================================================================

def reset_guidance_preferences() -> Dict[str, Any]:
    """Reset all onboarding status, tour completions, and workflow tracking preferences.
    
    Strictly preserves all search history, keyword tables, saved configurations,
    and studio profile credentials.
    """
    # 1. Clear database settings with guidance prefixes
    deleted_tours = db_manager.delete_settings_by_prefix("tour_")
    db_manager.delete_setting("user_onboarded_v17")
    db_manager.delete_setting("selected_onboarding_goal")
    db_manager.delete_setting("active_workflow_goal")
    db_manager.delete_settings_by_prefix("workflow_")

    # 2. Reset matching session state keys
    for key in list(st.session_state.keys()):
        if (
            key.startswith("tour_")
            or key.startswith("workflow_")
            or key in ["dismiss_onboarding_temp", "active_workflow_goal", "selected_onboarding_goal"]
        ):
            del st.session_state[key]

    return {"deleted_tours": deleted_tours, "status": "success"}
