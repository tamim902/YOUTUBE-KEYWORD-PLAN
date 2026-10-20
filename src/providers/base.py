"""Base abstract class for autocomplete providers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import threading

from src.models.keyword import AutocompleteResult


class BaseAutocompleteProvider(ABC):
    """Abstract interface for replaceable autocomplete suggestions providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_suggestions(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        cancellation_token: Optional[threading.Event] = None,
    ) -> List[AutocompleteResult]:
        """Fetch real-time autocomplete suggestions for a given query."""
        raise NotImplementedError
