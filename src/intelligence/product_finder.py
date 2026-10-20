"""Niche Product Discovery & AI-Powered Content Gap Intelligence (Phase 12 & Phase 13).

Provides:
- ProductExtractor: Multi-channel candidate product discovery, brand/model extraction, and AI/algorithmic query generation.
- ProductMatcher: Exact model matching, alias resolution, model generation preservation, and video evidence linking.
- ProductOpportunityScorer: Transparent 0–100 Research Opportunity Score with configurable factor weights and evidence confidence levels.
- NicheProductPipeline: Orchestrator for 60-day YouTube searches, matching, classification, scoring, report generation, and AI synthesis.
"""

from datetime import datetime, timedelta, timezone
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.models.product import (
    CandidateProduct,
    ClassificationCategory,
    ProductQueryExecution,
    ProductResearchSession,
    ProductVideoMatch,
    SearchMode,
)


def infer_product_category(product_name: str, niche: str = "") -> str:
    """Infer a standardized hardware/product sub-category from name and niche context."""
    p_lower = (product_name or "").lower()
    n_lower = (niche or "").lower()

    # Match specific product model / family keywords on product name first
    if any(k in p_lower for k in ("quietcomfort", "anc", "noise cancelling", "headphones", "over-ear")):
        return "Active Noise Cancelling (ANC)"
    elif any(k in p_lower for k in ("iem", "space travel", "airpods", "earfun", "in-ear", "in ear", "wf-1000", "buds")):
        return "In-Ear Monitors (IEMs)"
    elif any(k in p_lower for k in ("keychron", "wooting", "blackwidow", "apex pro", "rt100", "keyboard")):
        return "Custom Keyboards"
    elif any(k in p_lower for k in ("sm7b", "mv7", "at2020", "quadcast", "dynamic mic")):
        return "Dynamic Microphones"
    elif any(k in p_lower for k in ("superlight", "deathadder", "viper", "gaming mouse")):
        return "Wireless Gaming Mice"
    elif any(k in p_lower for k in ("fenix", "forerunner", "apple watch", "galaxy watch", "pixel watch", "fitbit")):
        return "Smart Wearables"
    elif any(k in p_lower for k in ("gopro", "action 5", "insta360", "pocket 3", "action cam")):
        return "Action Cameras"

    # Contextual fallback based on niche
    if any(k in n_lower for k in ("earbud", "tws", "earphone")):
        return "In-Ear Monitors (IEMs)"
    elif "headphone" in n_lower:
        return "Active Noise Cancelling (ANC)"
    elif "keyboard" in n_lower:
        return "Custom Keyboards"
    elif "mic" in n_lower:
        return "Dynamic Microphones"
    elif "mouse" in n_lower or "mice" in n_lower:
        return "Wireless Gaming Mice"
    elif "watch" in n_lower:
        return "Smart Wearables"
    elif "camera" in n_lower:
        return "Action Cameras"
    elif n_lower:
        return f"{niche.strip().title()} Accessory"
    return "Consumer Electronics"


class ProductExtractor:
    """Discovers and extracts candidate product names from keywords, titles, and user inputs."""

    # Curated real market product catalogs for popular hardware/consumer niches
    CURATED_NICHE_PRODUCTS: Dict[str, List[str]] = {
        "wireless earbuds": [
            "Sony WF-1000XM5",
            "Bose QuietComfort Ultra",
            "Apple AirPods Pro 2",
            "Sennheiser Momentum True Wireless 4",
            "Nothing Ear (2)",
            "Moondrop Space Travel",
            "Anker Soundcore Liberty 4 NC",
            "EarFun Air Pro 4",
            "Samsung Galaxy Buds 3 Pro",
            "JBL Live Beam 3",
        ],
        "earbuds": [
            "Sony WF-1000XM5",
            "Bose QuietComfort Ultra",
            "Apple AirPods Pro 2",
            "Nothing Ear (2)",
            "EarFun Air Pro 4",
            "SoundPEATS Capsule3 Pro+",
        ],
        "mechanical keyboards": [
            "Keychron Q1 Pro",
            "Keychron V1 Max",
            "Logitech G PRO X TKL",
            "Razer BlackWidow V4 Pro",
            "Corsair K70 MAX",
            "Wooting 60HE+",
            "NuPhy Air75 V2",
            "Epomaker RT100",
            "SteelSeries Apex Pro TKL",
            "DrunkDeer A75",
        ],
        "keyboards": [
            "Keychron Q1 Pro",
            "Keychron V1 Max",
            "Logitech G PRO X TKL",
            "Razer BlackWidow V4 Pro",
            "Wooting 60HE+",
        ],
        "smart watches": [
            "Apple Watch Ultra 2",
            "Samsung Galaxy Watch 7",
            "Garmin Fenix 8",
            "Garmin Forerunner 265",
            "Pixel Watch 3",
            "OnePlus Watch 2",
            "Amazfit Balance",
            "Fitbit Charge 6",
        ],
        "action cameras": [
            "GoPro HERO 13 Black",
            "DJI Osmo Action 5 Pro",
            "Insta360 Ace Pro 2",
            "Insta360 X4",
            "DJI Pocket 3",
            "Akaso Brave 7 LE",
        ],
        "microphones": [
            "Shure SM7B",
            "Rode Wireless PRO",
            "DJI Mic 2",
            "Shure MV7+",
            "Audio-Technica AT2020",
            "Elgato Wave:3",
            "HyperX QuadCast S",
            "Hollyland Lark M2",
        ],
    }

    # Common technology, electronics, and consumer product brand markers
    KNOWN_BRANDS = {
        "apple", "sony", "bose", "samsung", "sennheiser", "anker", "soundcore",
        "jabra", "nothing", "beats", "google", "moondrop", "audio-technica",
        "shure", "marshall", "jbl", "oneplus", "huawei", "xiaomi", "edifier",
        "logitech", "razer", "corsair", "steelseries", "keychron", "glorious",
        "asus", "dell", "lenovo", "hp", "acer", "lg", "fitbit", "garmin",
        "dji", "canon", "nikon", "fujifilm", "gopro", "insta360", "anker",
        "soundpeats", "akaso", "rode", "elgato", "hyperx", "wooting", "nuphy",
    }

    # Stopwords and noise terms to strip when extracting product names
    NOISE_WORDS = {
        "review", "unboxing", "vs", "versus", "test", "comparison", "best",
        "worth it", "buying guide", "top", "tips", "tricks", "sound test",
        "mic test", "full review", "long term", "after 1 month", "after 6 months",
        "2024", "2025", "2026", "2027", "bangla", "hindi", "honest", "dont buy",
        "watch before you buy", "hands on", "first look", "the complete",
    }

    def infer_product_category(self, product_name: str, niche: str = "") -> str:
        """Infer an appropriate high-level consumer category for the product candidate."""
        p_lower = (product_name or "").lower()
        n_lower = (niche or "").lower()

        if any(w in p_lower or w in n_lower for w in ("earbud", "headphone", "audio", "tws", "earphone", "anc")):
            return "Audio & Wearables"
        if any(w in p_lower or w in n_lower for w in ("keyboard", "mouse", "desk", "keychron", "keycap")):
            return "PC Peripherals"
        if any(w in p_lower or w in n_lower for w in ("watch", "fitness", "garmin", "fitbit", "smartwatch")):
            return "Wearable Technology"
        if any(w in p_lower or w in n_lower for w in ("camera", "gopro", "dji", "action cam", "lens")):
            return "Cameras & Imaging"
        if any(w in p_lower or w in n_lower for w in ("microphone", "mic", "shure", "rode")):
            return "Audio Recording"
        return niche.title() if niche else "Consumer Electronics"

    def get_curated_products_for_niche(self, niche: str) -> List[CandidateProduct]:
        """Return real market products for recognized niches if available."""
        niche_clean = niche.lower().strip()
        for key, prods in self.CURATED_NICHE_PRODUCTS.items():
            if key in niche_clean or niche_clean in key:
                res = []
                for p in prods:
                    parts = p.split(maxsplit=1)
                    b_name = parts[0].title() if len(parts) > 1 else ""
                    m_name = parts[1].strip() if len(parts) > 1 else p
                    cat = self.infer_product_category(p, niche)
                    res.append(
                        CandidateProduct(
                            product_name=p,
                            brand=b_name,
                            model=m_name,
                            niche=niche,
                            category=cat,
                            source="Curated Market Catalog",
                            evidence_reference=f"Curated {key.title()} Hardware Catalog",
                            verification_status="Verified Market Product",
                            extraction_confidence="High",
                            aliases=[f"{b_name} {m_name.replace('-', ' ')}"],
                        )
                    )
                return res
        return []

    def discover_candidates_from_autocomplete(
        self,
        niche: str,
        provider: Optional[Any] = None,
        language: str = "en",
        country: str = "US",
        limit: int = 15,
    ) -> List[CandidateProduct]:
        """Discover real product candidates for any niche using free YouTube autocomplete suggestions."""
        if not niche or not niche.strip():
            return []

        cur_year = datetime.now(timezone.utc).year
        seed_queries = [
            f"best {niche.strip()} {cur_year}",
            f"{niche.strip()} review",
            f"{niche.strip()} unboxing",
            f"{niche.strip()} vs ",
        ]

        discovered_candidates: List[CandidateProduct] = []
        if provider and hasattr(provider, "get_suggestions"):
            for sq in seed_queries:
                try:
                    res = provider.get_suggestions(sq, language=language, country=country)
                    for item in res:
                        text = getattr(item, "keyword", str(item))
                        candidates = self.extract_candidates_from_text(
                            text, niche=niche, source="Autocomplete Discovery"
                        )
                        for c in candidates:
                            c.evidence_reference = f"YouTube Autocomplete: '{sq}'"
                        discovered_candidates.extend(candidates)
                except Exception:
                    pass
        return discovered_candidates[:limit]

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize Unicode, whitespace, and strip common punctuation."""
        if not text:
            return ""
        norm = unicodedata.normalize("NFKC", text)
        return " ".join(norm.split())

    def extract_candidates_from_text(
        self,
        text: str,
        niche: str = "",
        source: str = "Extracted Candidate",
    ) -> List[CandidateProduct]:
        """Extract candidate product names from a query, keyword, or video title."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return []

        candidates: List[CandidateProduct] = []

        # Remove known noise words
        words = cleaned.split()
        filtered_words = []
        i = 0
        while i < len(words):
            w_clean = re.sub(r"[^\w\-\(\)\+]", "", words[i]).lower()
            if w_clean in self.NOISE_WORDS:
                i += 1
                continue
            filtered_words.append(words[i])
            i += 1

        filtered_text = " ".join(filtered_words)

        # 1. Look for known brand prefixes
        for brand in self.KNOWN_BRANDS:
            pattern = re.compile(rf"\b({re.escape(brand)})\b\s+([A-Za-z0-9\-\(\)\+\s]{{2,30}})", re.IGNORECASE)
            match = pattern.search(filtered_text)
            if match:
                b_name = match.group(1).title()
                model_part = match.group(2).strip()
                # Stop model at punctuation or noise keywords
                model_tokens = []
                for tok in model_part.split():
                    t_lower = re.sub(r"[^\w\-]", "", tok.lower())
                    if t_lower in self.NOISE_WORDS or t_lower in ("in", "for", "with", "and", "by"):
                        break
                    if t_lower in self.KNOWN_BRANDS and model_tokens:
                        break
                    model_tokens.append(tok)
                clean_model = " ".join(model_tokens).strip(" -:,")
                if clean_model and len(clean_model) >= 2:
                    full_name = f"{b_name} {clean_model}".strip()
                    # Determine confidence based on presence of model number/code
                    has_digits = bool(re.search(r"\d+", clean_model))
                    confidence = "High" if has_digits else "Moderate"
                    candidates.append(
                        CandidateProduct(
                            product_name=full_name,
                            brand=b_name,
                            model=clean_model,
                            niche=niche,
                            category=self.infer_product_category(full_name, niche),
                            source=source,
                            evidence_reference=f"Extracted from: '{text[:60]}'",
                            verification_status="Extracted Candidate",
                            extraction_confidence=confidence,
                            aliases=[f"{b_name} {clean_model.replace('-', ' ')}"],
                        )
                    )

        # 2. If no known brand found, check for alphanumeric model indicators
        if not candidates and len(filtered_words) >= 2:
            model_match = re.search(r"([A-Z][a-zA-Z0-9\-]+)\s+([A-Za-z0-9\-]+(?:\s+(?:Pro|Max|Ultra|Plus|Mini|SE|Air|\d+))?)", filtered_text)
            if model_match:
                possible_brand = model_match.group(1).title()
                possible_model = model_match.group(2).strip()
                candidates.append(
                    CandidateProduct(
                        product_name=f"{possible_brand} {possible_model}",
                        brand=possible_brand,
                        model=possible_model,
                        niche=niche,
                        category=self.infer_product_category(f"{possible_brand} {possible_model}", niche),
                        source=source,
                        evidence_reference=f"Extracted from: '{text[:60]}'",
                        verification_status="Needs Review",
                        extraction_confidence="Uncertain / Needs Review",
                        aliases=[],
                    )
                )

        return candidates

    def parse_seed_products(self, seed_products_text: str, niche: str = "") -> List[CandidateProduct]:
        """Parse user-supplied comma- or newline-separated seed products."""
        if not seed_products_text:
            return []

        lines = re.split(r"[\n,;]", seed_products_text)
        products: List[CandidateProduct] = []
        for line in lines:
            clean = self.clean_text(line)
            if clean and len(clean) >= 2:
                parts = clean.split(maxsplit=1)
                brand = parts[0].title() if len(parts) > 1 else ""
                model = parts[1].strip() if len(parts) > 1 else clean
                products.append(
                    CandidateProduct(
                        product_name=clean,
                        brand=brand,
                        model=model,
                        niche=niche,
                        category=self.infer_product_category(clean, niche),
                        source="User Supplied",
                        evidence_reference="User-Provided Seed Input",
                        verification_status="User Supplied",
                        extraction_confidence="High",
                        aliases=[],
                    )
                )
        return products

    def generate_search_queries(
        self,
        product: CandidateProduct,
        search_modes: Optional[List[str]] = None,
        ai_provider: Optional[Any] = None,
        year: Optional[int] = None,
        max_queries: int = 10,
        niche: str = "",
        **kwargs,
    ) -> List[Tuple[str, str, str]]:
        """Generate structured search queries for a product based on active search modes.

        Returns:
            List of 3-tuples: (query_string, search_mode_label, query_source).
            Backward-compatible with tuple slice [0] (query_text) and [1] (search_mode).
        """
        cur_year = year or datetime.now(timezone.utc).year
        name = product.product_name.strip()
        modes = search_modes or [
            SearchMode.REVIEWS.value,
            SearchMode.UNBOXING.value,
            SearchMode.COMPARISONS.value,
            SearchMode.BUYING_GUIDES.value,
        ]

        queries: List[Tuple[str, str, str]] = []
        seen_queries: Set[str] = set()

        def add_query(q_text: str, s_mode: str, source: str = "ALGORITHMIC_TEMPLATE") -> None:
            norm = q_text.lower().strip()
            if norm and norm not in seen_queries:
                seen_queries.add(norm)
                queries.append((q_text.strip(), s_mode, source))

        # 1. Algorithmic Template Generation across selected modes
        if SearchMode.REVIEWS.value in modes:
            add_query(f"{name} review", SearchMode.REVIEWS.value)
            add_query(f"{name} worth it", SearchMode.REVIEWS.value)

        if SearchMode.UNBOXING.value in modes:
            add_query(f"{name} unboxing", SearchMode.UNBOXING.value)

        if SearchMode.COMPARISONS.value in modes:
            add_query(f"{name} vs", SearchMode.COMPARISONS.value)

        if SearchMode.BUYING_GUIDES.value in modes:
            add_query(f"best {name} {cur_year}", SearchMode.BUYING_GUIDES.value)

        if SearchMode.ALTERNATIVES.value in modes:
            add_query(f"{name} alternatives", SearchMode.ALTERNATIVES.value)

        # Extended Phase 13 Search Modes
        if SearchMode.PRODUCT_TESTING.value in modes:
            add_query(f"{name} sound test", SearchMode.PRODUCT_TESTING.value)
            add_query(f"{name} battery test", SearchMode.PRODUCT_TESTING.value)

        if SearchMode.LONG_TERM_USE.value in modes:
            add_query(f"{name} after 6 months", SearchMode.LONG_TERM_USE.value)
            add_query(f"{name} long term review", SearchMode.LONG_TERM_USE.value)

        if SearchMode.COMMON_PROBLEMS.value in modes:
            add_query(f"{name} common issues", SearchMode.COMMON_PROBLEMS.value)
            add_query(f"{name} problems", SearchMode.COMMON_PROBLEMS.value)

        if SearchMode.TARGET_AUDIENCES.value in modes:
            add_query(f"{name} for gaming", SearchMode.TARGET_AUDIENCES.value)
            add_query(f"{name} for workout", SearchMode.TARGET_AUDIENCES.value)

        if SearchMode.USE_CASES.value in modes:
            add_query(f"{name} mic quality", SearchMode.USE_CASES.value)
            add_query(f"{name} anc performance", SearchMode.USE_CASES.value)

        if SearchMode.GENERAL.value in modes or not queries:
            add_query(f"{name}", SearchMode.GENERAL.value)

        # 2. Optional AI-Assisted Query Generation (labeled AI_GENERATED_QUERY)
        if ai_provider and hasattr(ai_provider, "generate_search_queries"):
            try:
                ai_angles = [m for m in modes if m in (
                    SearchMode.REVIEWS.value, SearchMode.UNBOXING.value, SearchMode.COMPARISONS.value,
                    SearchMode.PRODUCT_TESTING.value, SearchMode.LONG_TERM_USE.value, SearchMode.COMMON_PROBLEMS.value
                )]
                ai_results = ai_provider.generate_search_queries(
                    product_name=name,
                    brand=product.brand,
                    model=product.model,
                    niche=product.niche,
                    angles=ai_angles,
                    max_queries=5,
                )
                for item in ai_results:
                    if isinstance(item, (tuple, list)) and len(item) >= 2:
                        add_query(item[0], item[1], source="AI_GENERATED_QUERY")
            except Exception:
                pass

        return queries[:max_queries]


class ProductMatcher:
    """Compares candidate product names against video titles and descriptions."""

    @staticmethod
    def normalize_tokens(text: str) -> Set[str]:
        """Normalize text into lowercase alphanumeric word tokens, decomposing hyphens."""
        clean = unicodedata.normalize("NFKC", text or "").lower()
        words = re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", clean)
        tokens = set(words)
        for w in words:
            if "-" in w:
                for part in w.split("-"):
                    if part:
                        tokens.add(part)
        return tokens

    def is_match(
        self,
        product: CandidateProduct,
        video_title: str,
        video_description: str = "",
    ) -> Tuple[bool, str, str, List[str]]:
        """Evaluate if a video covers the candidate product.

        Returns:
            Tuple: (is_matched, match_type, match_field, matched_terms).
            match_type: "Exact Model Match", "Alias Match", "Token / Partial Match", or "None".
        """
        title_norm = unicodedata.normalize("NFKC", video_title or "").lower()
        desc_norm = unicodedata.normalize("NFKC", video_description or "").lower()

        p_name = product.product_name.lower().strip()
        brand = product.brand.lower().strip() if product.brand else ""
        model = product.model.lower().strip() if product.model else ""

        title_tokens = self.normalize_tokens(video_title)
        model_tokens = self.normalize_tokens(model) if model else set()

        # 1. Exact Full Product Name match in title
        if p_name and p_name in title_norm:
            return (True, "Exact Model Match", "title", [p_name])

        # 2. Check Aliases in title
        for alias in product.aliases:
            a_clean = alias.lower().strip()
            if a_clean and a_clean in title_norm:
                return (True, "Alias Match", "title", [alias])

        # 3. Model Token Check (Crucial: prevents cross-generation false matches like XM4 matching XM5)
        if model and brand:
            has_brand = brand in title_norm or brand in title_tokens
            if has_brand and model_tokens:
                if model_tokens.issubset(title_tokens):
                    matched_terms = [brand] + list(model_tokens)
                    return (True, "Exact Model Match", "title", matched_terms)

        # 4. Check description if title didn't match
        if p_name and len(p_name) > 4 and p_name in desc_norm:
            return (True, "Exact Model Match", "description", [p_name])

        for alias in product.aliases:
            a_clean = alias.lower().strip()
            if a_clean and a_clean in desc_norm:
                return (True, "Alias Match", "description", [alias])

        return (False, "None", "", [])


class ProductOpportunityScorer:
    """Calculates an explainable 0–100 Research Opportunity Score with customizable weights."""

    def calculate_score(
        self,
        product: CandidateProduct,
        few_videos_threshold: int = 3,
        min_queries_for_zero_match: int = 2,
        weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, str, str, Dict[str, Any]]:
        """Calculate score, classification category, confidence, and transparent breakdown.

        Returns:
            Tuple of (score, classification, confidence_level, score_breakdown).
        """
        matching_count = product.matching_videos_count
        succeeded_count = product.queries_succeeded
        queries_count = max(len(product.queries_executed), succeeded_count)

        # Detect unverified product identity
        is_unverified = (
            product.verification_status in ("Needs Review", "Unverified", "Rejected")
            or product.extraction_confidence in ("Uncertain / Needs Review", "Low")
        )

        # 5-Tier Classification Logic (Phase 13 Section 4)
        if is_unverified:
            classification = ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value
            reason = "Candidate product identity is unverified against a known brand or hardware model."
        elif queries_count == 0 or succeeded_count == 0:
            classification = ClassificationCategory.INSUFFICIENT_RESEARCH.value
            reason = "No successful search queries have been executed for this product yet."
        elif matching_count == 0:
            if succeeded_count >= min_queries_for_zero_match:
                classification = ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value
                reason = (
                    f"0 matching videos retrieved across {succeeded_count} executed search queries in the selected period "
                    f"(meets required minimum coverage of {min_queries_for_zero_match} queries)."
                )
            else:
                classification = ClassificationCategory.INSUFFICIENT_RESEARCH.value
                reason = (
                    f"Only {succeeded_count} query executed with 0 results; requires at least {min_queries_for_zero_match} "
                    f"queries before concluding zero matching videos in the period."
                )
        elif matching_count < few_videos_threshold:
            classification = ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value
            reason = f"Only {matching_count} matching videos found in search sample (below few-videos threshold of {few_videos_threshold})."
        else:
            classification = ClassificationCategory.MATCHING_VIDEOS_FOUND.value
            reason = f"{matching_count} matching videos found in the selected period."

        # Factor 1: Scarcity / Gap Opportunity Factor (0 to 40 pts)
        if classification in (ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value, ClassificationCategory.NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES.value):
            opp_factor = 40.0
        elif classification == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value:
            if matching_count == 1:
                opp_factor = 32.0
            elif matching_count == 2:
                opp_factor = 25.0
            else:
                opp_factor = 20.0
        elif classification == ClassificationCategory.MATCHING_VIDEOS_FOUND.value:
            if matching_count <= 5:
                opp_factor = 14.0
            else:
                opp_factor = 6.0
        else:  # INSUFFICIENT_RESEARCH or PRODUCT_IDENTITY_UNVERIFIED
            opp_factor = 15.0

        # Factor 2: Search Coverage Factor (0 to 25 pts)
        if succeeded_count >= 3:
            coverage_factor = 25.0
        elif succeeded_count == 2:
            coverage_factor = 18.0
        elif succeeded_count == 1:
            coverage_factor = 10.0
        else:
            coverage_factor = 0.0

        # Factor 3: Product Identity Confidence (0 to 20 pts)
        if product.verification_status in ("Verified Market Product", "User Supplied"):
            identity_factor = 20.0
        elif product.extraction_confidence == "High":
            identity_factor = 16.0
        elif product.extraction_confidence == "Moderate":
            identity_factor = 11.0
        else:
            identity_factor = 5.0

        # Factor 4: Niche Relevance & Keyword Evidence (0 to 15 pts)
        if product.source in ("Existing Keywords", "User Supplied", "Curated Market Catalog"):
            niche_factor = 15.0
        elif product.source in ("Video Titles", "Autocomplete Discovery"):
            niche_factor = 12.0
        else:
            niche_factor = 8.0

        # Apply configurable factor weights if supplied
        w = weights or {"scarcity": 1.0, "coverage": 1.0, "identity": 1.0, "relevance": 1.0}
        w_scarcity = max(0.1, float(w.get("scarcity", 1.0)))
        w_coverage = max(0.1, float(w.get("coverage", 1.0)))
        w_identity = max(0.1, float(w.get("identity", 1.0)))
        w_relevance = max(0.1, float(w.get("relevance", 1.0)))

        # Normalize weights so sum of maximums equals 100.0
        max_weighted = (40.0 * w_scarcity) + (25.0 * w_coverage) + (20.0 * w_identity) + (15.0 * w_relevance)
        scale = 100.0 / max(1.0, max_weighted)

        opp_pts = round(opp_factor * w_scarcity * scale, 1)
        cov_pts = round(coverage_factor * w_coverage * scale, 1)
        ident_pts = round(identity_factor * w_identity * scale, 1)
        niche_pts = round(niche_factor * w_relevance * scale, 1)

        total_score = round(opp_pts + cov_pts + ident_pts + niche_pts, 1)
        total_score = max(0.0, min(100.0, total_score))

        # Confidence level derived from evidence completeness & verification
        if classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value:
            confidence = "Low"
            total_score = min(total_score, 50.0)
        elif classification == ClassificationCategory.INSUFFICIENT_RESEARCH.value:
            confidence = "Low"
            total_score = min(total_score, 45.0)
        elif is_unverified:
            confidence = "Low"
            total_score = min(total_score, 55.0)
        elif succeeded_count >= 2 and product.extraction_confidence in ("High", "Verified"):
            confidence = "High"
        elif succeeded_count >= 1:
            confidence = "Moderate"
        else:
            confidence = "Low"

        breakdown = {
            "opportunity_factor": opp_pts,
            "search_coverage_factor": cov_pts,
            "identity_confidence_factor": ident_pts,
            "niche_relevance_factor": niche_pts,
            "weights_applied": {"scarcity": w_scarcity, "coverage": w_coverage, "identity": w_identity, "relevance": w_relevance},
            "total_score": total_score,
            "classification": classification,
            "confidence_level": confidence,
            "classification_reason": reason,
            "inputs_from_retrieved_data": [
                f"Matching videos retrieved: {matching_count}",
                f"Executed queries: {succeeded_count} / {queries_count}",
                f"Latest video date: {product.latest_video_date or 'None'}",
            ],
            "inputs_from_user_preferences": [
                f"Few videos threshold: {few_videos_threshold}",
                f"Min queries for zero match: {min_queries_for_zero_match}",
                f"Product Source: {product.source}",
            ],
            "empirical_limitation_notice": (
                "Observed research finding within the executed search sample for the specified period. "
                "Does NOT prove complete platform-wide absence of videos on YouTube."
            ),
            "formula_explanation": (
                f"Research Opportunity Score = Scarcity ({opp_pts} pts) + Search Coverage ({cov_pts} pts) + "
                f"Identity Confidence ({ident_pts} pts) + Niche Relevance ({niche_pts} pts). "
                "Represents content gap research priority within the searched sample, "
                "NOT guaranteed search volume, difficulty, or platform-wide absence."
            ),
        }

        return total_score, classification, confidence, breakdown


class NicheProductPipeline:
    """Orchestrates candidate product gathering, date-bounded searches, matching, and scoring."""

    def __init__(
        self,
        extractor: Optional[ProductExtractor] = None,
        matcher: Optional[ProductMatcher] = None,
        scorer: Optional[ProductOpportunityScorer] = None,
    ) -> None:
        self.extractor = extractor or ProductExtractor()
        self.matcher = matcher or ProductMatcher()
        self.scorer = scorer or ProductOpportunityScorer()

    @staticmethod
    def get_default_date_range(days: int = 60) -> Tuple[str, str]:
        """Return RFC 3339 strings for previous N days (start_date, end_date)."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        return (start.isoformat(), now.isoformat())

    def validate_date_range(self, start_date_iso: str, end_date_iso: str) -> Tuple[bool, str]:
        """Validate start and end dates."""
        try:
            st_clean = start_date_iso.replace("Z", "+00:00")
            en_clean = end_date_iso.replace("Z", "+00:00")
            dt_start = datetime.fromisoformat(st_clean)
            dt_end = datetime.fromisoformat(en_clean)
            if dt_start.tzinfo is None:
                dt_start = dt_start.replace(tzinfo=timezone.utc)
            if dt_end.tzinfo is None:
                dt_end = dt_end.replace(tzinfo=timezone.utc)
            if dt_start > dt_end:
                return (False, "Start date cannot be after end date.")
            if dt_end > datetime.now(timezone.utc) + timedelta(days=1):
                return (False, "End date cannot be in the future.")
            return (True, "Date range is valid.")
        except Exception as ex:
            return (False, f"Invalid ISO date format: {str(ex)}")

    def estimate_quota_cost(
        self,
        products_count: int,
        search_modes_count: int = 3,
        cost_per_query: int = 101,
    ) -> int:
        """Estimate required YouTube API quota units."""
        return products_count * search_modes_count * cost_per_query

    def generate_research_report(
        self,
        session: ProductResearchSession,
        products: List[CandidateProduct],
        queries_executed: Optional[List[ProductQueryExecution]] = None,
        is_live: bool = False,
        ai_summary: str = "",
    ) -> Dict[str, Any]:
        """Generate a complete structured research report for export and executive review."""
        q_list = queries_executed or []
        succeeded = sum(1 for q in q_list if getattr(q, "status", "") == "Success")
        failed = sum(1 for q in q_list if getattr(q, "status", "") == "Error")
        data_mode_label = "LIVE RESEARCH — YOUTUBE DATA API V3" if is_live else "TEST DATA — NOT LIVE RESEARCH"

        # Classification breakdowns
        cnt_gap = sum(1 for p in products if p.classification in (
            ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
            ClassificationCategory.NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES.value,
        ))
        cnt_few = sum(1 for p in products if p.classification == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value)
        cnt_found = sum(1 for p in products if p.classification == ClassificationCategory.MATCHING_VIDEOS_FOUND.value)
        cnt_insufficient = sum(1 for p in products if p.classification == ClassificationCategory.INSUFFICIENT_RESEARCH.value)
        cnt_unverified = sum(1 for p in products if p.classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value)

        ranked = sorted(products, key=lambda p: p.opportunity_score, reverse=True)

        return {
            "session_metadata": {
                "niche": session.niche,
                "country": session.country,
                "language": session.language,
                "start_date": session.start_date,
                "end_date": session.end_date,
                "data_mode": data_mode_label,
                "is_live": is_live,
                "created_at": session.created_at,
            },
            "summary_counts": {
                "total_candidates": len(products),
                "zero_observed_gaps": cnt_gap,
                "few_matching_videos": cnt_few,
                "matching_videos_found": cnt_found,
                "insufficient_research": cnt_insufficient,
                "unverified_identities": cnt_unverified,
            },
            "query_telemetry": {
                "total_queries_executed": len(q_list),
                "queries_succeeded": succeeded,
                "queries_failed": failed,
                "quota_used": session.quota_used,
            },
            "ai_synthesis": ai_summary or session.ai_summary or "No executive synthesis generated.",
            "ranked_products": [p.to_dict() for p in ranked],
            "empirical_notice": (
                "Observed research findings in the executed YouTube search sample for the specified period. "
                "Does NOT prove complete platform-wide absence of videos on YouTube."
            ),
        }
