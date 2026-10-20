"""Product Opportunity Ranking & Affiliate Content Planning Intelligence (Phase 14).

Provides:
- OpportunityScorerV14: Multi-factor heuristic scoring (v14.0)
- ContentFormatRecommender: Rule-based video format matching across 9 strategic types
- AffiliateBriefGenerator: Evidence-grounded content brief synthesis with FTC disclosures
- ProductComparisonEngine: Side-by-side opportunity matrix builder with missing metric handling
"""

from typing import Any, Dict, List, Optional, Tuple

from src.models.product_planner import (
    AffiliateContentBrief,
    AffiliateProductData,
    ContentFormatRecommendation,
    ProductOpportunityShortlist,
    ShortlistStatus,
)


class OpportunityScorerV14:
    """Calculates a transparent, multi-factor opportunity score (0-100, v14.0).

    IMPORTANT:
    This is an evidence-based content planning heuristic, NOT an indicator
    of guaranteed search volume, profitability, or ranking probability.
    """

    VERSION = "v14.0"

    # Default factor weights (sum to 100)
    DEFAULT_WEIGHTS = {
        "identity_verification": 20,
        "niche_relevance": 15,
        "keyword_evidence": 15,
        "research_coverage": 20,
        "video_scarcity": 20,
        "evidence_completeness": 10,
    }

    def __init__(self, weights: Optional[Dict[str, int]] = None) -> None:
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def calculate_score(
        self,
        is_identity_verified: bool,
        has_niche_match: bool,
        supporting_keywords_count: int,
        queries_executed_count: int,
        matching_videos_count: int,
        has_merchant_data: bool = False,
        has_affiliate_info: bool = False,
        brand_identified: bool = True,
    ) -> Tuple[float, str, Dict[str, Any]]:
        """Calculate opportunity score, confidence level, and detailed factor breakdown.

        Returns:
            Tuple of (score: float, confidence_level: str, breakdown: dict)
        """
        breakdown: Dict[str, Any] = {}
        raw_score = 0.0

        # 1. Identity Verification (max 20 pts)
        max_id = self.weights.get("identity_verification", 20)
        id_score = 0.0
        if is_identity_verified:
            id_score = max_id
        elif brand_identified:
            id_score = max_id * 0.5  # Brand known, model not fully verified
        else:
            id_score = max_id * 0.1
        breakdown["identity_verification"] = round(id_score, 1)
        raw_score += id_score

        # 2. Niche Relevance (max 15 pts)
        max_niche = self.weights.get("niche_relevance", 15)
        niche_score = max_niche if has_niche_match else max_niche * 0.3
        breakdown["niche_relevance"] = round(niche_score, 1)
        raw_score += niche_score

        # 3. Keyword Evidence / Search Intent (max 15 pts)
        max_kw = self.weights.get("keyword_evidence", 15)
        if supporting_keywords_count >= 5:
            kw_score = max_kw
        elif supporting_keywords_count >= 3:
            kw_score = max_kw * 0.8
        elif supporting_keywords_count >= 1:
            kw_score = max_kw * 0.5
        else:
            kw_score = max_kw * 0.2
        breakdown["keyword_evidence"] = round(kw_score, 1)
        raw_score += kw_score

        # 4. Research Coverage (max 20 pts)
        max_cov = self.weights.get("research_coverage", 20)
        if queries_executed_count >= 4:
            cov_score = max_cov
        elif queries_executed_count >= 2:
            cov_score = max_cov * 0.75
        elif queries_executed_count == 1:
            cov_score = max_cov * 0.3
        else:
            cov_score = 0.0
        breakdown["research_coverage"] = round(cov_score, 1)
        raw_score += cov_score

        # 5. Video Scarcity (max 20 pts)
        # Scarcity only rewards if research coverage is sufficient!
        max_scarcity = self.weights.get("video_scarcity", 20)
        if queries_executed_count < 2:
            # Cannot claim scarcity without at least 2 distinct queries searched
            scarcity_score = max_scarcity * 0.2
            scarcity_reason = "Insufficient query coverage to confirm scarcity"
        elif matching_videos_count == 0:
            scarcity_score = max_scarcity
            scarcity_reason = "Zero matching videos observed across executed queries"
        elif matching_videos_count <= 2:
            scarcity_score = max_scarcity * 0.75
            scarcity_reason = f"Few matching videos ({matching_videos_count}) observed"
        elif matching_videos_count <= 5:
            scarcity_score = max_scarcity * 0.4
            scarcity_reason = f"Moderate competition ({matching_videos_count} videos)"
        else:
            scarcity_score = max_scarcity * 0.1
            scarcity_reason = f"High competition ({matching_videos_count} videos)"

        breakdown["video_scarcity"] = round(scarcity_score, 1)
        breakdown["scarcity_reason"] = scarcity_reason
        raw_score += scarcity_score

        # 6. Evidence Completeness (max 10 pts)
        max_comp = self.weights.get("evidence_completeness", 10)
        comp_score = 0.0
        if has_merchant_data:
            comp_score += max_comp * 0.5
        if has_affiliate_info:
            comp_score += max_comp * 0.5
        breakdown["evidence_completeness"] = round(comp_score, 1)
        raw_score += comp_score

        final_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Confidence Level & Guardrail Caps
        confidence = "Moderate Evidence"
        guardrails_applied: List[str] = []

        if queries_executed_count < 2:
            confidence = "Low Evidence"
            if final_score > 40.0:
                final_score = 40.0
                guardrails_applied.append(
                    "Capped at 40 due to insufficient research coverage (<2 queries)"
                )

        if not is_identity_verified:
            if final_score > 50.0:
                final_score = 50.0
                guardrails_applied.append(
                    "Capped at 50 due to unverified product identity"
                )
            if confidence != "Low Evidence":
                confidence = "Moderate Evidence"

        if queries_executed_count >= 3 and is_identity_verified and supporting_keywords_count >= 2:
            confidence = "High Evidence"

        breakdown["guardrails_applied"] = guardrails_applied
        breakdown["formula_version"] = self.VERSION

        return final_score, confidence, breakdown


class ContentFormatRecommender:
    """Recommends content formats based on product category, keywords, and search signals."""

    @staticmethod
    def recommend_formats(
        product_name: str,
        category: str = "",
        keywords: Optional[List[str]] = None,
        matching_videos_count: int = 0,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Determine primary format and secondary options with rationales.

        Returns:
            Tuple of (primary_format: str, alternatives: List[dict])
        """
        kw_text = " ".join(keywords or []).lower()
        prod_lower = product_name.lower()
        cat_lower = category.lower()

        primary = ContentFormatRecommendation.PRODUCT_REVIEW.value
        alternatives: List[Dict[str, str]] = []

        # Rule evaluation
        if any(term in kw_text for term in ["vs", "versus", "or", "better than"]):
            primary = ContentFormatRecommendation.PRODUCT_COMPARISON.value
            primary_reason = "Search terms contain direct comparison intent ('vs', 'or')."
        elif any(term in kw_text for term in ["how to", "setup", "install", "guide", "connect"]):
            primary = ContentFormatRecommendation.BEGINNER_TUTORIAL.value
            primary_reason = "Search terms focus on setup or usage tutorials."
        elif any(term in kw_text for term in ["problem", "fix", "issue", "not working", "troubleshooting"]):
            primary = ContentFormatRecommendation.PROBLEM_SOLVING.value
            primary_reason = "Troubleshooting and problem resolution queries identified."
        elif any(term in kw_text for term in ["mistake", "worth it", "don't buy", "regret"]):
            primary = ContentFormatRecommendation.COMMON_MISTAKES.value
            primary_reason = "Buyer hesitation and mistake-avoidance intent detected."
        elif any(term in kw_text for term in ["unboxing", "first look", "package"]):
            primary = ContentFormatRecommendation.UNBOXING.value
            primary_reason = "Explicit unboxing interest in supporting keywords."
        elif matching_videos_count == 0:
            primary = ContentFormatRecommendation.PRODUCT_REVIEW.value
            primary_reason = "Zero observed matching videos: First comprehensive review has high gap potential."
        else:
            primary = ContentFormatRecommendation.PRODUCT_REVIEW.value
            primary_reason = "Core physical product evaluation format."

        # Secondary recommendations
        all_formats = [
            (
                ContentFormatRecommendation.PRODUCT_COMPARISON.value,
                "Position against the closest category benchmark or preceding model.",
            ),
            (
                ContentFormatRecommendation.ALTERNATIVES.value,
                "Present as a budget or feature alternative to popular market leaders.",
            ),
            (
                ContentFormatRecommendation.BUYING_GUIDE.value,
                "Include as a top recommendation inside a broader niche category roundup.",
            ),
            (
                ContentFormatRecommendation.BEGINNER_TUTORIAL.value,
                "Step-by-step setup, pairing, or configuration guide.",
            ),
            (
                ContentFormatRecommendation.COMMON_MISTAKES.value,
                "Highlight key buyer misconceptions or setup pitfalls to avoid.",
            ),
            (
                ContentFormatRecommendation.LONG_TERM_REVIEW.value,
                "Evaluate durability, battery degradation, and long-term value.",
            ),
            (
                ContentFormatRecommendation.PROBLEM_SOLVING.value,
                "Focus on resolving specific consumer friction points.",
            ),
        ]

        for fmt, desc in all_formats:
            if fmt != primary:
                alternatives.append({"format": fmt, "rationale": desc})

        return primary, alternatives[:4]


class AffiliateBriefGenerator:
    """Generates structured, evidence-grounded affiliate content briefs."""

    @staticmethod
    def generate_brief(
        shortlist: ProductOpportunityShortlist,
        primary_keyword: Optional[str] = None,
        competitor_links: Optional[List[Dict[str, Any]]] = None,
    ) -> AffiliateContentBrief:
        """Create a complete editable brief."""
        p_name = shortlist.product_name
        brand = shortlist.brand or ""
        model = shortlist.model or ""
        pk = primary_keyword or f"{p_name} review"

        supporting = shortlist.supporting_keywords or [
            f"{p_name} specs",
            f"{p_name} price",
            f"{p_name} vs",
            f"best {shortlist.niche or 'gear'}",
        ]

        title_ideas = [
            f"{p_name} In-Depth Review: Worth Buying in 2026?",
            f"Before You Buy {p_name} - Real Specs & Features Checked",
            f"{p_name} vs The Competition: Is It Really Better?",
            f"The Truth About {p_name} (What Reviews Don't Tell You)",
        ]

        video_structure = [
            {"section": "00:00 - Hook & Overview", "notes": f"Introduce {p_name}, price point, and target user."},
            {"section": "01:30 - Key Specifications", "notes": "Verify manufacturer claimed specs vs observed details."},
            {"section": "04:00 - Performance & Features", "notes": "Hands-on demonstration or documented capability analysis."},
            {"section": "08:00 - Strengths & Weaknesses", "notes": "Objective pros and cons based on verifiable facts."},
            {"section": "11:00 - Alternatives & Comparison", "notes": "Compare against similar products in the price tier."},
            {"section": "13:30 - Verdict & Affiliate CTA", "notes": "Final recommendation with transparent FTC disclosure."},
        ]

        questions = [
            f"What makes {p_name} stand out in the {shortlist.niche or 'market'} category?",
            f"What are the verified battery/build specifications for model {model or p_name}?",
            f"Is the current price competitive compared to similar alternatives?",
            "What common complaints or setup difficulties have users reported?",
        ]

        features_to_verify = [
            "Official manufacturer retail price and active discounts",
            "Box contents and included accessories",
            "Warranty coverage and manufacturer support",
            "Key technical specifications (weight, dimensions, battery life, compatibility)",
        ]

        pros_cons = {
            "pros": [
                f"Documented features for {p_name}",
                "Competitive price point in niche tier",
            ],
            "cons": [
                "Requires verification of long-term reliability",
                "Limited third-party benchmark data currently available",
            ],
        }

        fact_checks = [
            {"task": "Verify exact model number and retail packaging", "status": "Pending"},
            {"task": "Verify official price from merchant before publishing", "status": "Pending"},
            {"task": "Confirm affiliate link destination matches promised merchant", "status": "Pending"},
            {"task": "Verify no unsupported claims of personal testing are made", "status": "Pending"},
            {"task": "Ensure FTC affiliate disclosure is spoken and written in description", "status": "Pending"},
        ]

        cta = (
            f"If you'd like to check current pricing or purchase the {p_name}, "
            "use the verified link in the description below."
        )

        disclosure = (
            "FTC Compliance Disclosure: State clearly at the start of the video and in the first lines of the description: "
            "'Disclosure: Some links in this description are affiliate links. If you purchase through them, I may earn a small commission at no additional cost to you.'"
        )

        return AffiliateContentBrief(
            shortlist_id=shortlist.id,
            product_id=shortlist.product_id,
            product_name=p_name,
            primary_keyword=pk,
            brand=brand,
            model=model,
            category=shortlist.category or shortlist.niche,
            supporting_keywords=supporting,
            target_audience=f"Buyers interested in {shortlist.niche or 'consumer products'}",
            search_intent="Commercial Investigation",
            content_format=shortlist.intended_format or ContentFormatRecommendation.PRODUCT_REVIEW.value,
            title_ideas=title_ideas,
            video_structure=video_structure,
            questions_to_investigate=questions,
            features_to_verify=features_to_verify,
            pros_and_cons=pros_cons,
            competitor_references=competitor_links or [],
            call_to_action=cta,
            affiliate_disclosure=disclosure,
            fact_checking_checklist=fact_checks,
            brief_notes=shortlist.notes or "",
        )


class ProductComparisonEngine:
    """Generates side-by-side comparison matrices with rigorous missing-metric handling."""

    @staticmethod
    def build_comparison_matrix(
        products: List[ProductOpportunityShortlist],
    ) -> Dict[str, Any]:
        """Build matrix where missing values are 'Unavailable' / 'N/A', NEVER 0.

        Returns dictionary suitable for table rendering and export.
        """
        rows = []
        for p in products:
            aff = p.affiliate_data or {}
            price_val = aff.get("price")
            currency_val = aff.get("currency", "USD")

            if price_val is not None and price_val > 0:
                price_str = f"${price_val:,.2f} {currency_val}"
            else:
                price_str = "Unavailable"

            merchant_str = aff.get("merchant") or "Needs verification"
            program_str = aff.get("affiliate_program") or "Needs verification"
            commission_str = aff.get("commission_info") or "Needs verification"
            avail_str = aff.get("availability") or "Unknown"

            row = {
                "Product Name": p.product_name,
                "Brand": p.brand if p.brand else "Unavailable",
                "Model": p.model if p.model else "Unavailable",
                "Opportunity Score": p.opportunity_score,
                "Confidence": p.confidence_level,
                "Matching Videos (Observed)": p.matching_videos_count,
                "Queries Executed": p.queries_executed_count,
                "Workflow Status": p.status,
                "Priority": p.priority,
                "Intended Format": p.intended_format,
                "Price": price_str,
                "Merchant": merchant_str,
                "Affiliate Program": program_str,
                "Commission Structure": commission_str,
                "Availability": avail_str,
                "Identity Verified": "Yes" if p.verification_checklist.get("identity_verified") else "No",
                "Evidence Caution": "Observed gap in search results; does not guarantee sales volume.",
            }
            rows.append(row)

        return {
            "matrix_rows": rows,
            "disclaimer": (
                "NOTE: Video scarcity reflects observed search results within the selected period and query set. "
                "Low video count alone is not evidence of consumer demand or affiliate revenue potential."
            ),
        }
