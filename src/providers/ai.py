"""AI Provider Interface and Implementations for Niche Research (Phase 13).

Provides:
- BaseAiProvider: Abstract interface for AI query generation and report summarization.
- DeterministicFallbackAiProvider: 100% offline, rule-based intelligence for query expansion and synthesis.
- GeminiAiProvider: Google Gemini REST API integration using secure key configuration.
- OpenAiProvider: OpenAI REST API integration using secure key configuration.
- MockAiProvider: Fixture provider for deterministic automated testing.
- get_ai_provider: Factory function to resolve available or preferred AI provider.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import unicodedata
import requests


class BaseAiProvider(ABC):
    """Abstract base class for AI query generation and research summarization."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a human-readable name of the provider."""
        pass

    @abstractmethod
    def generate_search_queries(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        niche: str = "",
        angles: Optional[List[str]] = None,
        search_modes: Optional[List[str]] = None,
        max_queries: int = 5,
        **kwargs,
    ) -> List[Tuple[str, str, str]]:
        """Generate structured search queries for a candidate product.

        Returns:
            List of 3-tuples: (query_text, search_angle_label, query_source).
        """
        pass

    @abstractmethod
    def generate_research_summary(
        self,
        session_data: Optional[Dict[str, Any]] = None,
        products: Optional[List[Any]] = None,
        executed_queries_count: int = 0,
        niche: str = "",
        session_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Generate an executive markdown research synthesis based strictly on collected evidence."""
        pass


class DeterministicFallbackAiProvider(BaseAiProvider):
    """100% offline, local intelligence provider requiring zero external API keys."""

    EXTENDED_ANGLE_TEMPLATES: Dict[str, List[str]] = {
        "Product Reviews": ["{name} review", "{name} worth it", "{name} honest review"],
        "Reviews": ["{name} review", "{name} worth it", "{name} honest review"],
        "Unboxing": ["{name} unboxing", "{name} first look", "{name} unboxing setup"],
        "Comparisons": ["{name} vs", "{name} compared to", "{name} vs competitors"],
        "Buying Guides": ["best {name}", "should you buy {name}", "is {name} worth buying"],
        "Alternatives": ["{name} alternatives", "cheaper alternative to {name}"],
        "Product Testing": ["{name} sound test", "{name} latency test", "{name} battery test"],
        "Long-Term Use": ["{name} after 6 months", "{name} long term review", "{name} 1 year later"],
        "Common Problems": ["{name} common issues", "{name} problems", "{name} fix"],
        "Target Audiences": ["{name} for gaming", "{name} for workout", "{name} for students"],
        "Different Use Cases": ["{name} mic quality", "{name} anc performance", "{name} daily use"],
        "Use Cases": ["{name} mic quality", "{name} anc performance", "{name} daily use"],
    }

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Local Deterministic Intelligence (Offline)"

    def generate_search_queries(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        niche: str = "",
        angles: Optional[List[str]] = None,
        search_modes: Optional[List[str]] = None,
        max_queries: int = 5,
        **kwargs,
    ) -> List[Tuple[str, str, str]]:
        clean_name = " ".join(product_name.strip().split())
        if not clean_name:
            return []

        selected_angles = angles or search_modes or list(self.EXTENDED_ANGLE_TEMPLATES.keys())[:5]
        generated: List[Tuple[str, str, str]] = []
        seen_queries = set()

        for angle in selected_angles:
            templates = self.EXTENDED_ANGLE_TEMPLATES.get(angle, [f"{{name}} {angle.lower()}"])
            for tpl in templates:
                q = tpl.format(name=clean_name).strip()
                norm_q = q.lower()
                if norm_q not in seen_queries:
                    seen_queries.add(norm_q)
                    generated.append((q, angle, "AI_GENERATED_QUERY"))
                if len(generated) >= max_queries:
                    break
            if len(generated) >= max_queries:
                break

        return generated[:max_queries]

    def generate_research_summary(
        self,
        session_data: Optional[Dict[str, Any]] = None,
        products: Optional[List[Any]] = None,
        executed_queries_count: int = 0,
        niche: str = "",
        session_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Produce an empirical synthesis without external API dependencies."""
        sess_dict = dict(session_data or {})
        if niche:
            sess_dict["niche"] = niche
        if session_params:
            sess_dict.update(session_params)

        prods = products or []
        niche_name = sess_dict.get("niche", niche or "Product Niche")
        start_dt = str(sess_dict.get("start_date", ""))[:10]
        end_dt = str(sess_dict.get("end_date", ""))[:10]
        total_prods = len(prods)

        # Classification counts
        gaps = [p for p in prods if getattr(p, "classification", "") in ("NO MATCHING VIDEOS FOUND IN SEARCHES", "NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES", "NO MATCHING VIDEOS FOUND")]
        few = [p for p in prods if getattr(p, "classification", "") == "FEW MATCHING VIDEOS FOUND"]
        found = [p for p in prods if getattr(p, "classification", "") == "MATCHING VIDEOS FOUND"]
        insufficient = [p for p in prods if getattr(p, "classification", "") == "INSUFFICIENT RESEARCH"]
        unverified = [p for p in prods if getattr(p, "classification", "") == "PRODUCT IDENTITY UNVERIFIED"]

        top_opportunities = sorted(
            prods,
            key=lambda x: getattr(x, "opportunity_score", 0.0),
            reverse=True,
        )[:3]

        lines = [
            f"### 📋 Executive Research Summary: {niche_name}",
            f"**Research Window:** `{start_dt}` to `{end_dt}` | **Executed Queries:** `{executed_queries_count}` | **Candidates Analyzed:** `{total_prods}`\n",
            "#### 📊 VERIFIED EMPIRICAL RESEARCH FINDINGS (Search Sample)",
            f"- **Observed Content Gaps (0 Matches in Sample):** **{len(gaps)}** products",
            f"- **Few Matching Videos (< Few-Threshold):** **{len(few)}** products",
            f"- **Established Video Coverage:** **{len(found)}** products",
            f"- **Insufficient Research Coverage:** **{len(insufficient)}** products",
            f"- **Unverified Product Identities:** **{len(unverified)}** products\n",
        ]

        if top_opportunities:
            lines.append("#### 💡 STRATEGIC CONTENT OPPORTUNITIES & INTERPRETATIONS")
            for idx, p in enumerate(top_opportunities, 1):
                p_name = getattr(p, "product_name", "Unknown")
                score = getattr(p, "opportunity_score", 0.0)
                cat = getattr(p, "classification", "")
                v_count = getattr(p, "matching_videos_count", 0)
                conf = getattr(p, "confidence_level", "Moderate")
                lines.append(
                    f"{idx}. **{p_name}** — Research Opportunity Score: `{score:.1f}/100` ({conf} Evidence)\n"
                    f"   - **Status:** `{cat}` ({v_count} matching videos retrieved in executed search sample)\n"
                    f"   - **Content Angle:** High content gap in recent window; recommended for honest review or testing."
                )
            lines.append("")

        lines.extend([
            "#### ❓ MISSING EVIDENCE & UNCERTAINTIES",
            f"- {len(unverified)} candidate products require identity verification against known physical hardware manufacturers.",
            f"- {len(insufficient)} candidates had fewer successful queries than required minimum coverage for reliable gap determination.\n",
            "#### ⚠️ EMPIRICAL RESEARCH LIMITATION NOTICE",
            "- **Sample-Bounded Research**: Absence of videos in the executed search sample confirms an observed content gap in YouTube search results, but does not prove complete platform-wide absence.",
            "- **Zero Synthetic Metrics Guarantee**: Scores reflect observed search scarcity and verification, not search volume estimates or traffic promises.",
        ])

        return "\n".join(lines)


class GeminiAiProvider(BaseAiProvider):
    """Google Gemini REST API integration using secure key configuration."""

    API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 12.0):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        self.fallback = DeterministicFallbackAiProvider()

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def get_provider_name(self) -> str:
        return "Google Gemini AI (Cloud API)"

    def generate_search_queries(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        niche: str = "",
        angles: Optional[List[str]] = None,
        max_queries: int = 5,
    ) -> List[Tuple[str, str]]:
        if not self.is_available():
            return self.fallback.generate_search_queries(product_name, brand, model, niche, angles, max_queries)

        selected_angles = angles or ["Product Reviews", "Unboxing", "Comparisons", "Long-Term Use", "Common Problems"]
        prompt = (
            f"You are a YouTube research specialist. Given the real product '{product_name}' in the niche '{niche}', "
            f"generate up to {max_queries} highly realistic, natural YouTube search queries across these specific angles: {', '.join(selected_angles)}.\n"
            "STRICT RULES:\n"
            "1. Do NOT invent new products, fake features, prices, or search volume metrics.\n"
            "2. Output strictly a JSON array of objects with keys 'query' (the exact search string) and 'angle' (the search angle).\n"
            "3. Example format: [{\"query\": \"Sony WF-1000XM5 review\", \"angle\": \"Product Reviews\"}]"
        )

        try:
            url = f"{self.API_ENDPOINT}?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            }
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                results: List[Tuple[str, str]] = []
                for item in parsed:
                    q = item.get("query", "").strip()
                    ang = item.get("angle", "Product Reviews").strip()
                    if q:
                        results.append((q, ang))
                if results:
                    return results[:max_queries]
        except Exception:
            pass

        # Fallback on transient error or invalid response
        return self.fallback.generate_search_queries(product_name, brand, model, niche, angles, max_queries)

    def generate_research_summary(
        self,
        session_data: Dict[str, Any],
        products: List[Any],
        executed_queries_count: int = 0,
    ) -> str:
        if not self.is_available():
            return self.fallback.generate_research_summary(session_data, products, executed_queries_count)

        summary_payload = []
        for p in products[:10]:
            summary_payload.append({
                "product_name": getattr(p, "product_name", ""),
                "classification": getattr(p, "classification", ""),
                "videos_count": getattr(p, "matching_videos_count", 0),
                "score": getattr(p, "opportunity_score", 0.0),
                "confidence": getattr(p, "confidence_level", ""),
                "verification": getattr(p, "verification_status", ""),
            })

        prompt = (
            f"You are a YouTube product intelligence analyst. Summarize this niche research session in clean Markdown.\n"
            f"Niche: {session_data.get('niche')}\n"
            f"Date Range: {session_data.get('start_date', '')[:10]} to {session_data.get('end_date', '')[:10]}\n"
            f"Queries Executed: {executed_queries_count}\n"
            f"Investigated Products Data: {json.dumps(summary_payload)}\n"
            "STRICT RULES:\n"
            "1. Reference ONLY the actual collected records provided above.\n"
            "2. Separate empirical facts from strategic interpretations.\n"
            "3. State the query coverage and sample size clearly.\n"
            "4. NEVER invent search volume numbers, guaranteed views, or platform-wide absence.\n"
            "5. Include sections: Executive Synthesis, Top Verified Content Gaps, and Research Limitations."
        )

        try:
            url = f"{self.API_ENDPOINT}?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3},
            }
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception:
            pass

        return self.fallback.generate_research_summary(session_data, products, executed_queries_count)


class OpenAiProvider(BaseAiProvider):
    """OpenAI REST API integration using secure key configuration."""

    API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 12.0):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        self.fallback = DeterministicFallbackAiProvider()

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def get_provider_name(self) -> str:
        return "OpenAI (GPT-4o-mini)"

    def generate_search_queries(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        niche: str = "",
        angles: Optional[List[str]] = None,
        max_queries: int = 5,
    ) -> List[Tuple[str, str]]:
        if not self.is_available():
            return self.fallback.generate_search_queries(product_name, brand, model, niche, angles, max_queries)

        selected_angles = angles or ["Product Reviews", "Unboxing", "Comparisons", "Long-Term Use", "Common Problems"]
        prompt = (
            f"Generate up to {max_queries} natural YouTube search queries for '{product_name}' in niche '{niche}' "
            f"across angles: {', '.join(selected_angles)}. Output JSON array of objects with keys 'query' and 'angle'."
        )

        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            resp = requests.post(self.API_ENDPOINT, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"]
                parsed = json.loads(raw_text)
                items = parsed.get("queries") if "queries" in parsed else (parsed if isinstance(parsed, list) else [])
                results = [(it["query"], it.get("angle", "Product Reviews")) for it in items if "query" in it]
                if results:
                    return results[:max_queries]
        except Exception:
            pass

        return self.fallback.generate_search_queries(product_name, brand, model, niche, angles, max_queries)

    def generate_research_summary(
        self,
        session_data: Optional[Dict[str, Any]] = None,
        products: Optional[List[Any]] = None,
        executed_queries_count: int = 0,
        niche: str = "",
        session_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        return self.fallback.generate_research_summary(
            session_data=session_data,
            products=products,
            executed_queries_count=executed_queries_count,
            niche=niche,
            session_params=session_params,
            **kwargs,
        )


class MockAiProvider(BaseAiProvider):
    """Mock AI Provider for deterministic unit testing."""

    def __init__(
        self,
        predefined_queries: Optional[List[Any]] = None,
        predefined_summary: str = "",
    ):
        self.predefined_queries = predefined_queries or [
            ("Mocked Review Query", "Reviews", "AI_GENERATED_QUERY"),
            ("Mocked Unboxing Query", "Unboxing", "AI_GENERATED_QUERY"),
        ]
        self.predefined_summary = predefined_summary
        self.call_history: List[Dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Mock AI Test Provider"

    def generate_search_queries(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        niche: str = "",
        angles: Optional[List[str]] = None,
        search_modes: Optional[List[str]] = None,
        max_queries: int = 5,
        **kwargs,
    ) -> List[Tuple[str, str, str]]:
        self.call_history.append({"action": "generate_queries", "product": product_name, "niche": niche})
        modes = angles or search_modes or ["Reviews", "Unboxing"]
        res = []
        for m in modes:
            res.append((f"{product_name} {m.lower()} query", m, "AI_GENERATED_QUERY"))
            if len(res) >= max_queries:
                break
        return res if res else [(f"{product_name} review", "Reviews", "AI_GENERATED_QUERY")][:max_queries]

    def generate_research_summary(
        self,
        session_data: Optional[Dict[str, Any]] = None,
        products: Optional[List[Any]] = None,
        executed_queries_count: int = 0,
        niche: str = "",
        session_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        self.call_history.append({"action": "generate_summary", "products_count": len(products or [])})
        if self.predefined_summary:
            return self.predefined_summary
        n = niche or (session_data.get("niche") if session_data else "Product Niche")
        prods = products or []
        prod_names = ", ".join(getattr(p, "product_name", str(p)) for p in prods)
        return (
            f"### Mock AI Research Summary: {n}\n"
            f"#### 📊 VERIFIED EMPIRICAL RESEARCH FINDINGS & FACTS (Search Sample)\n"
            f"- Candidates Analyzed: {len(prods)} ({prod_names})\n"
            f"#### 💡 STRATEGIC CONTENT OPPORTUNITIES & INTERPRETATIONS\n"
            f"- Key mock opportunities identified for {prod_names}.\n"
            f"#### ⚠️ EMPIRICAL RESEARCH LIMITATION NOTICE\n"
            f"- Observed findings only."
        )


def get_ai_provider(
    provider_type: Optional[str] = None,
    api_key: Optional[str] = None,
    db_manager: Optional[Any] = None,
) -> BaseAiProvider:
    """Resolve and return an AI provider instance based on settings or availability."""
    p_choice = (provider_type or "").lower().strip()
    if p_choice == "mock":
        return MockAiProvider()

    gemini_key = api_key or ""
    openai_key = api_key or ""
    if db_manager:
        if not gemini_key:
            gemini_key = db_manager.get_setting("gemini_api_key", "")
        if not openai_key:
            openai_key = db_manager.get_setting("openai_api_key", "")
    if not gemini_key:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not openai_key:
        openai_key = os.getenv("OPENAI_API_KEY", "")

    if "gemini" in p_choice and gemini_key:
        return GeminiAiProvider(api_key=gemini_key)
    if "openai" in p_choice and openai_key:
        return OpenAiProvider(api_key=openai_key)

    if p_choice in ("deterministic", "offline", "fallback"):
        return DeterministicFallbackAiProvider()

    # Default to deterministic offline provider
    return DeterministicFallbackAiProvider()
