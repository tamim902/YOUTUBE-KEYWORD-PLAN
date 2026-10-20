"""Bilingual pattern template definitions for English and Bangla."""

import unicodedata
from typing import Dict, List
from src.patterns.models import PatternCategory

# General comparison templates (applied without requiring specific alternatives)
# and Specific comparison templates (requiring verified alternatives)
COMPARISON_GENERAL_EN = [
    "[keyword] vs alternatives",
    "[keyword] comparison",
]

COMPARISON_SPECIFIC_EN = [
    "[keyword] vs [alternative]",
    "difference between [keyword] and [alternative]",
]

COMPARISON_GENERAL_BN = [
    "[keyword] বনাম অন্যান্য",
    "[keyword] তুলনা",
]

COMPARISON_SPECIFIC_BN = [
    "[keyword] বনাম [alternative]",
    "[keyword] এবং [alternative] এর পার্থক্য",
]

# English pattern templates
EN_TEMPLATES: Dict[PatternCategory, List[str]] = {
    PatternCategory.LISTICLES: [
        "top 5 [keyword]",
        "top 10 [keyword]",
        "best 5 [keyword]",
        "best 10 [keyword]",
        "top tips for [keyword]",
        "top tools for [keyword]",
        "top [keyword] ideas",
    ],
    PatternCategory.BEST_BUYING: [
        "best [keyword]",
        "best [keyword] for beginners",
        "best budget [keyword]",
        "affordable [keyword]",
        "[keyword] buying guide",
        "is [keyword] worth it",
    ],
    PatternCategory.REVIEWS: [
        "[keyword] review",
        "[keyword] honest review",
        "[keyword] detailed review",
        "[keyword] comparison review",
    ],
    PatternCategory.HOW_TO: [
        "how to [keyword]",
        "how to use [keyword]",
        "[keyword] tutorial",
        "[keyword] step by step",
        "[keyword] for beginners",
        "[keyword] tips and tricks",
    ],
    PatternCategory.COMPARISON: COMPARISON_GENERAL_EN,
    PatternCategory.QUESTIONS: [
        "what is [keyword]",
        "how does [keyword] work",
        "why is [keyword] important",
        "when to use [keyword]",
        "which [keyword] is best",
        "can beginners use [keyword]",
    ],
    PatternCategory.AUDIENCE: [
        "[keyword] for beginners",
        "[keyword] for students",
        "[keyword] for small business",
        "[keyword] for daily use",
        "[keyword] at home",
        "[keyword] on a budget",
    ],
    PatternCategory.TIME_MODIFIERS: [
        "best [keyword] [current_year]",
        "[keyword] guide [current_year]",
        "new [keyword] [current_year]",
        "[keyword] updates [current_year]",
    ],
}

# Bangla pattern templates (strictly NFC normalized)
BN_TEMPLATES: Dict[PatternCategory, List[str]] = {
    PatternCategory.LISTICLES: [
        "সেরা ৫ [keyword]",
        "সেরা ১০ [keyword]",
        "শীর্ষ ৫ [keyword]",
        "শীর্ষ ১০ [keyword]",
        "[keyword] সেরা টিপস",
        "[keyword] সেরা উপায়",
        "[keyword] সেরা আইডিয়া",
    ],
    PatternCategory.BEST_BUYING: [
        "সেরা [keyword]",
        "নতুনদের জন্য সেরা [keyword]",
        "কম বাজেটে সেরা [keyword]",
        "সাশ্রয়ী [keyword]",
        "[keyword] কেনার গাইড",
        "[keyword] কেনা উচিত কি না",
    ],
    PatternCategory.REVIEWS: [
        "[keyword] রিভিউ",
        "[keyword] বাংলা রিভিউ",
        "[keyword] বিস্তারিত রিভিউ",
        "[keyword] সৎ রিভিউ",
    ],
    PatternCategory.HOW_TO: [
        "কিভাবে [keyword] করবেন",
        "[keyword] ব্যবহারের নিয়ম",
        "[keyword] টিউটোরিয়াল",
        "ধাপে ধাপে [keyword]",
        "নতুনদের জন্য [keyword]",
        "[keyword] টিপস এবং ট্রিকস",
    ],
    PatternCategory.COMPARISON: COMPARISON_GENERAL_BN,
    PatternCategory.QUESTIONS: [
        "[keyword] কি",
        "কিভাবে [keyword] কাজ করে",
        "কেন [keyword] গুরুত্বপূর্ণ",
        "কখন [keyword] ব্যবহার করবেন",
        "কোন [keyword] টি সেরা",
        "নতুনরা কি [keyword] শিখতে পারে",
    ],
    PatternCategory.AUDIENCE: [
        "নতুনদের জন্য [keyword]",
        "শিক্ষার্থীদের জন্য [keyword]",
        "ছোট ব্যবসার জন্য [keyword]",
        "দৈনন্দিন ব্যবহারের জন্য [keyword]",
        "ঘরে বসে [keyword]",
        "কম খরচে [keyword]",
    ],
    PatternCategory.TIME_MODIFIERS: [
        "সেরা [keyword] [current_year]",
        "[keyword] গাইড [current_year]",
        "নতুন [keyword] [current_year]",
        "[keyword] আপডেট [current_year]",
    ],
}

# Ensure all strings in templates are NFC normalized
def _normalize_dict(d: Dict[PatternCategory, List[str]]) -> Dict[PatternCategory, List[str]]:
    return {
        cat: [unicodedata.normalize("NFC", t) for t in templates]
        for cat, templates in d.items()
    }

EN_TEMPLATES = _normalize_dict(EN_TEMPLATES)
BN_TEMPLATES = _normalize_dict(BN_TEMPLATES)
COMPARISON_GENERAL_EN = [unicodedata.normalize("NFC", t) for t in COMPARISON_GENERAL_EN]
COMPARISON_SPECIFIC_EN = [unicodedata.normalize("NFC", t) for t in COMPARISON_SPECIFIC_EN]
COMPARISON_GENERAL_BN = [unicodedata.normalize("NFC", t) for t in COMPARISON_GENERAL_BN]
COMPARISON_SPECIFIC_BN = [unicodedata.normalize("NFC", t) for t in COMPARISON_SPECIFIC_BN]
