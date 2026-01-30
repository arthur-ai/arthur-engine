import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from clients.currency.abc_currency_rate_provider import ABCCurrencyRateProvider

logger = logging.getLogger(__name__)

CONVERSION_PRECISION = 6
SIX_HOURS_SECONDS = 6 * 3600


def _next_six_hour_boundary_utc() -> float:
    """Return seconds from now until the next 00:00, 06:00, 12:00, or 18:00 UTC."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    next_bucket = ((hour // 6) + 1) * 6
    if next_bucket == 24:
        next_run = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        next_run = now.replace(hour=next_bucket, minute=0, second=0, microsecond=0)
    return (next_run - now).total_seconds()


class CurrencyConversionService:
    """
    In-memory cache of USD exchange rates with a background thread that refreshes
    every 6 hours at 00:00, 06:00, 12:00, 18:00 UTC. Falls back to USD on errors.
    """

    def __init__(self) -> None:
        self._rates: dict[str, float] = {}
        self._lock = threading.RLock()
        self._last_updated: Optional[datetime] = None
        self._provider: Optional[ABCCurrencyRateProvider] = None
        self._shutdown_event = threading.Event()
        self._background_thread: Optional[threading.Thread] = None

    def convert_usd_to(
        self, amount_usd: float, target_currency: str
    ) -> tuple[float, str]:
        """
        Convert an amount from USD to the target currency.

        Returns (converted_amount, currency_code). If target is USD, rate is
        missing, or any error occurs, returns (amount_usd, "USD") (unconverted).
        """
        try:
            target = (target_currency or "").strip().upper()
            if not target or target == "USD":
                return (amount_usd, "USD")
            with self._lock:
                rate = self._rates.get(target)
            if rate is None:
                return (amount_usd, "USD")
            converted = round(amount_usd * rate, CONVERSION_PRECISION)
            return (converted, target)
        except Exception as e:
            logger.warning("Currency conversion failed, returning USD: %s", e)
            return (amount_usd, "USD")

    def has_rates(self) -> bool:
        """Return True if the cache has at least one rate (e.g. after first successful refresh)."""
        with self._lock:
            return len(self._rates) > 0

    def _refresh(self) -> None:
        """Fetch rates from the provider and update the cache. On error, leave cache unchanged."""
        if not self._provider:
            return
        try:
            rates = self._provider.fetch_rates("USD")
            if "USD" not in rates:
                rates["USD"] = 1.0
            with self._lock:
                self._rates = rates
                self._last_updated = datetime.now(timezone.utc)
            logger.info(
                "Currency rates refreshed: %s currencies, last_updated=%s",
                len(self._rates),
                self._last_updated.isoformat(),
            )
        except Exception as e:
            logger.warning(
                "Failed to refresh currency rates, keeping previous cache: %s", e
            )

    def _scheduler_loop(self) -> None:
        """Run in background: fetch once immediately, then at each 6-hour boundary UTC."""
        self._refresh()
        while not self._shutdown_event.is_set():
            sleep_seconds = _next_six_hour_boundary_utc()
            if sleep_seconds <= 0:
                sleep_seconds = SIX_HOURS_SECONDS
            if self._shutdown_event.wait(timeout=sleep_seconds):
                break
            self._refresh()
            if self._shutdown_event.wait(timeout=SIX_HOURS_SECONDS):
                break
        logger.info("Currency conversion scheduler thread exiting")

    def load_rates_from_provider(self, provider: ABCCurrencyRateProvider) -> None:
        """Load rates once from the provider without starting the background thread. Use for static provider."""
        with self._lock:
            self._provider = provider
        self._refresh()
        logger.info("Currency conversion service loaded rates (no background thread)")

    def start(self, provider: ABCCurrencyRateProvider) -> None:
        """Start the service with the given provider and begin the refresh thread."""
        with self._lock:
            if (
                self._background_thread is not None
                and self._background_thread.is_alive()
            ):
                logger.info("Currency conversion service already started")
                return
            self._provider = provider
            self._shutdown_event.clear()
        self._background_thread = threading.Thread(
            target=self._scheduler_loop,
            name="currency-conversion-refresh",
            daemon=True,
        )
        self._background_thread.start()
        logger.info("Currency conversion service started")

    def shutdown(self, timeout: float = 30.0) -> None:
        """Signal the background thread to exit and wait up to timeout seconds."""
        self._shutdown_event.set()
        if self._background_thread:
            self._background_thread.join(timeout=timeout)
            if self._background_thread.is_alive():
                logger.warning("Currency conversion thread did not exit within timeout")
            self._background_thread = None
        logger.info("Currency conversion service stopped")


_singleton: Optional[CurrencyConversionService] = None


def get_currency_conversion_service() -> CurrencyConversionService:
    """Return the singleton CurrencyConversionService (not started)."""
    global _singleton
    if _singleton is None:
        _singleton = CurrencyConversionService()
    return _singleton


def initialize_currency_conversion_service() -> None:
    """Create the service singleton and start or load provider. Call from app lifespan."""
    from clients.currency.frankfurter_provider import FrankfurterCurrencyRateProvider
    from clients.currency.static_provider import StaticCurrencyRateProvider
    from config.currency_config import currency_config

    service = get_currency_conversion_service()
    if currency_config.CURRENCY_PROVIDER == "static":
        if currency_config.CURRENCY_EXCHANGE_RATE is None:
            logger.warning(
                "CURRENCY_PROVIDER=static but CURRENCY_EXCHANGE_RATE is not set; "
                "conversion will fall back to USD until configured."
            )
        service.load_rates_from_provider(
            StaticCurrencyRateProvider(config=currency_config)
        )
    else:
        service.start(FrankfurterCurrencyRateProvider(config=currency_config))


def shutdown_currency_conversion_service(timeout: float = 30.0) -> None:
    """Stop the currency conversion refresh thread. Call from app lifespan before yield ends."""
    global _singleton
    if _singleton is not None:
        _singleton.shutdown(timeout=timeout)
