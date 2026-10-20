"""Rule patterns and semantic triggers for bilingual intent classification (English & Bangla)."""

import re
from typing import Dict, List, Pattern, Tuple
from src.classifier.models import SearchIntent

# English and Bangla intent regex patterns and heuristic base confidence weights
INTENT_RULES: List[Tuple[SearchIntent, List[Pattern[str]], float, str]] = [
    # 1. Question Intent
    (
        SearchIntent.QUESTION,
        [
            re.compile(r"^(what|why|how|when|where|who|which|can|is|are|does|do|should|could|would)\b", re.IGNORECASE),
            re.compile(r"\b(how to|how does|why is|what is|when to|which is)\b", re.IGNORECASE),
            re.compile(r"\?$", re.UNICODE),
            # Bangla Question markers
            re.compile(r"(^|\s)(কি|কী|কেন|কিভাবে|কীভাবে|কখন|কোথায়|কোথায়|কোন|কোনটি|কার|কাকে)(\s|$)", re.UNICODE),
            re.compile(r"(হবে কি|কিনা|উচিত কি)", re.UNICODE),
        ],
        0.90,
        "Matched interrogative question pattern or prefix",
    ),
    # 2. Listicle / Best List
    (
        SearchIntent.LISTICLE,
        [
            re.compile(r"\b(top|best)\s+\d+\b", re.IGNORECASE),
            re.compile(r"\b\d+\s+(best|top|ways|tips|tools|ideas|steps|reasons|rules)\b", re.IGNORECASE),
            re.compile(r"\b(top tips|top tools|top ideas|top ways)\b", re.IGNORECASE),
            # Bangla Listicle markers
            re.compile(r"(সেরা|শীর্ষ)\s+[০-৯0-9]+", re.UNICODE),
            re.compile(r"[০-৯0-9]+\s*টি\s*(সেরা|উপায়|টিপস)", re.UNICODE),
            re.compile(r"(সেরা টিপস|সেরা উপায়|সেরা আইডিয়া)", re.UNICODE),
        ],
        0.95,
        "Matched numbered listicle or ranked list pattern",
    ),
    # 3. Review Intent
    (
        SearchIntent.REVIEW,
        [
            re.compile(r"\b(review|reviews|honest review|detailed review|hands on|unboxing|rating|ratings|worth it)\b", re.IGNORECASE),
            # Bangla Review markers
            re.compile(r"(রিভিউ|মতামত|পর্যালোচনা|কেমন|কেনা উচিত কি না)", re.UNICODE),
        ],
        0.90,
        "Matched product review, unboxing, or appraisal terms",
    ),
    # 4. Tutorial / How-To Intent
    (
        SearchIntent.TUTORIAL,
        [
            re.compile(r"\b(how to|tutorial|tutorials|guide|step by step|for beginners|learn|course|setup|install|installation|walkthrough)\b", re.IGNORECASE),
            # Bangla Tutorial markers
            re.compile(r"(কিভাবে|কীভাবে|টিউটোরিয়াল|টিউটোরিয়াল|গাইড|ধাপে ধাপে|নতুনদের জন্য|সহজে শেখার|ব্যবহারের নিয়ম)", re.UNICODE),
        ],
        0.90,
        "Matched instructional, tutorial, or setup guide pattern",
    ),
    # 5. Comparison Intent
    (
        SearchIntent.COMPARISON,
        [
            re.compile(r"\b(vs|versus|difference between|compared to|comparison|alternatives?)\b", re.IGNORECASE),
            # Bangla Comparison markers
            re.compile(r"(বনাম|তুলনা|পার্থক্য|বিকল্প)", re.UNICODE),
        ],
        0.95,
        "Matched head-to-head comparison or alternative term",
    ),
    # 6. Buying Intent
    (
        SearchIntent.BUYING_INTENT,
        [
            re.compile(r"\b(buy|price|cost|discount|deal|deals|cheap|affordable|budget|where to buy|purchase|order|coupon)\b", re.IGNORECASE),
            # Bangla Buying Intent markers
            re.compile(r"(দাম|মূল্য|কিনবেন|কেনার|সাশ্রয়ী|সাশ্রয়ী|কম বাজেটে|বাজেট|অফার|ডিসকাউন্ট)", re.UNICODE),
        ],
        0.85,
        "Matched commercial or transactional buying triggers",
    ),
    # 7. Commercial Investigation Intent
    (
        SearchIntent.COMMERCIAL_INVESTIGATION,
        [
            re.compile(r"\b(best|top|compare|pros and cons|which is best|recommended|buying guide)\b", re.IGNORECASE),
            # Bangla Commercial Investigation markers
            re.compile(r"(সেরা|শীর্ষ|সবচেয়ে ভালো|কেনার গাইড|সুবিধা এবং অসুবিধা)", re.UNICODE),
        ],
        0.80,
        "Matched top recommendation or commercial investigation keywords",
    ),
    # 8. Problem-solving Intent
    (
        SearchIntent.PROBLEM_SOLVING,
        [
            re.compile(r"\b(fix|solve|solution|problem|issues?|troubleshoot|troubleshooting|remove|error|fail|failed|haze|haziness|scratches?|streaks?|swirls?|residue|stains?|repair)\b", re.IGNORECASE),
            # Bangla Problem-solving markers
            re.compile(r"(সমস্যা|সমাধান|ত্রুটি|দূর করার|দাগ তোলার|মেরামত)", re.UNICODE),
        ],
        0.88,
        "Matched problem-solving, defect repair, or troubleshooting terms",
    ),
    # 9. Audience-specific Intent
    (
        SearchIntent.AUDIENCE_SPECIFIC,
        [
            re.compile(r"\b(for beginners?|for seniors?|for kids?|for pros?|for professionals?|for men|for women|for students?|for developers?|for black cars?|for white cars?|for dark cars?|for red cars?|for old cars?|for new cars?|for daily drivers?)\b", re.IGNORECASE),
            # Bangla Audience-specific markers
            re.compile(r"(নতুনদের জন্য|শিক্ষার্থীদের জন্য|গাড়ির জন্য|বিশেষজ্ঞদের জন্য|কালো গাড়ির জন্য)", re.UNICODE),
        ],
        0.85,
        "Matched specific target audience, car color, or user segment",
    ),
    # 10. Location-specific Intent
    (
        SearchIntent.LOCATION_SPECIFIC,
        [
            re.compile(r"\b(near me|in [a-zA-Z]+|local|in bangladesh|in bd|in usa|in uk|in canada|in india|in dhaka)\b", re.IGNORECASE),
            # Bangla Location-specific markers
            re.compile(r"(বাংলাদেশে|কাছে|নিকটস্থ|ঢাকা|চট্টগ্রাম)", re.UNICODE),
        ],
        0.82,
        "Matched geographic location or proximity marker",
    ),
    # 11. Informational Intent
    (
        SearchIntent.INFORMATIONAL,
        [
            re.compile(r"\b(what is|definition|meaning|explained|overview|history|architecture|features|basics|fundamentals)\b", re.IGNORECASE),
            # Bangla Informational markers
            re.compile(r"(পরিচিতি|অর্থ|ইতিহাস|মূল বিষয়|ব্যাখ্যা)", re.UNICODE),
        ],
        0.75,
        "Matched informational definitions, fundamentals, or background terms",
    ),
]
