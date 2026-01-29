from abc import ABC, abstractmethod


class ABCCurrencyRateProvider(ABC):
    """Abstract base class for currency exchange rate providers."""

    @abstractmethod
    def fetch_rates(self, base_currency: str) -> dict[str, float]:
        """
        Fetch exchange rates for the given base currency.

        Args:
            base_currency: ISO 4217 currency code (e.g. "USD").

        Returns:
            Dict mapping target currency codes to the rate (amount per 1 unit of base).
            E.g. {"EUR": 0.92, "GBP": 0.79} for base USD means 1 USD = 0.92 EUR.

        Raises:
            Exception: On network errors, HTTP errors, or parse failures.
        """
        raise NotImplementedError
