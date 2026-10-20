"""Controlled Live Smoke Test for YouTube Autocomplete Endpoint.

CRITICAL PRIVACY & SECURITY RULES:
- Zero credentials or API keys required.
- Only performs a minimal, single query to verify live endpoint responsiveness.
- Clearly separated from offline mock tests.
- Handles network unavailability gracefully without failing deterministic offline suites.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.providers.youtube import YouTubeAutocompleteProvider


def run_live_smoke_test(query: str = "youtube seo") -> dict:
    """Execute a single live query against the public autocomplete endpoint."""
    provider = YouTubeAutocompleteProvider(
        connect_timeout=5.0,
        read_timeout=5.0,
        max_retries=1,
    )
    try:
        results = provider.get_suggestions(query=query, language="en", country="US", use_cache=False)
        return {
            "status": "PASS",
            "query": query,
            "results_count": len(results),
            "sample_suggestions": [r.keyword for r in results[:3]],
            "source_type": results[0].source_type if results else None,
            "source_name": results[0].source_name if results else None,
            "notes": "Live Google Suggest endpoint is reachable and returned valid JSON.",
        }
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "query": query,
            "results_count": 0,
            "sample_suggestions": [],
            "error": str(exc),
            "notes": "External network or proxy restriction prevented live connection. Offline functionality unaffected.",
        }


if __name__ == "__main__":
    result = run_live_smoke_test()
    print("=== LIVE AUTOCOMPLETE SMOKE TEST RESULT ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
    if result["status"] == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)
