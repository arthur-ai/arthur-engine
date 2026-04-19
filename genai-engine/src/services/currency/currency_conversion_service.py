import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from clients.currency.abc_currency_rate_provider import ABCCurrencyRateProvider
from clients.currency.frankfurter_provider import FrankfurterCurrencyRateProvider
from clients.currency.static_provider import StaticCurrencyRateProvider
from config.currency_config import currency_config
from services.base_queue_service import BaseQueueJob, BaseQueueService

logger = logging.getLogger(__name__)

CONVERSION_PRECISION = 6
SIX_HOURS_SECONDS = 6 * 3600

CURRENCY_REFRESH_JOB_KEY = "currency_refresh"


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


class CurrencyRefreshJob(BaseQueueJob):
    """Job representing a single currency rate refresh."""

    def __init__(self, delay_seconds: int = 0) -> None:
        super().__init__(delay_seconds=delay_seconds)


class CurrencyConversionService(BaseQueueService[CurrencyRefreshJob]):
    """
    In-memory cache of USD exchange rates with a background thread that refreshes
    every 6 hours at 00:00, 06:00, 12:00, 18:00 UTC. Falls back to USD on errors.
    """

    job_model = CurrencyRefreshJob
    service_name = "currency_conversion_service"
    background_thread_name = "currency-conversion-refresh"

    def __init__(
        self,
        num_workers: int = 1,
        override_execution_delay: Optional[int] = None,
    ) -> None:
        super().__init__(
            num_workers=num_workers,
            override_execution_delay=override_execution_delay,
        )
        self._rates: dict[str, float] = {}
        self._lock = threading.RLock()
        self._last_updated: Optional[datetime] = None
        self._provider: Optional[ABCCurrencyRateProvider] = None

    def _get_job_key(self, job: CurrencyRefreshJob) -> str:
        """Use a constant key so at most one refresh job is active at a time."""
        return CURRENCY_REFRESH_JOB_KEY

    def _execute_job(self, job: CurrencyRefreshJob) -> None:
        """Perform a single rate refresh."""
        self._refresh()

    def _background_loop(self) -> None:
        """Run in background: fetch once immediately, then enqueue refresh at each 6-hour boundary UTC."""
        logger.info(f"Background thread started for {self.service_name}")
        self._refresh()
        while not self.shutdown_event.is_set():
            sleep_seconds = _next_six_hour_boundary_utc()
            if sleep_seconds <= 0:
                sleep_seconds = SIX_HOURS_SECONDS
            wait_time = min(sleep_seconds, SIX_HOURS_SECONDS)
            if self.shutdown_event.wait(timeout=wait_time):
                break
            self.enqueue(CurrencyRefreshJob(delay_seconds=0))
        logger.info(f"Background thread stopped for {self.service_name}")

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

    def load_rates_from_provider(self, provider: ABCCurrencyRateProvider) -> None:
        """Load rates once from the provider without starting the background thread. Use for static provider."""
        with self._lock:
            self._provider = provider
        self._refresh()
        logger.info("Currency conversion service loaded rates (no background thread)")

    def start(self) -> None:
        """Start the service: load provider from config, then either load once (static) or start background thread (Frankfurter)."""
        provider: ABCCurrencyRateProvider
        if currency_config.CURRENCY_PROVIDER == "static":
            if currency_config.CURRENCY_EXCHANGE_RATE is None:
                logger.warning(
                    "CURRENCY_PROVIDER=static but CURRENCY_EXCHANGE_RATE is not set; "
                    "conversion will fall back to USD until configured."
                )
            provider = StaticCurrencyRateProvider(config=currency_config)
            self.load_rates_from_provider(provider)
            return
        provider = FrankfurterCurrencyRateProvider(config=currency_config)
        with self._lock:
            self._provider = provider
        super().start()


CURRENCY_CONVERSION_SERVICE: CurrencyConversionService | None = None


def get_currency_conversion_service() -> CurrencyConversionService | None:
    """Get the global currency conversion service instance."""
    return CURRENCY_CONVERSION_SERVICE


def initialize_currency_conversion_service() -> None:
    """Initialize and start the global currency conversion service."""
    global CURRENCY_CONVERSION_SERVICE
    if CURRENCY_CONVERSION_SERVICE is None:
        CURRENCY_CONVERSION_SERVICE = CurrencyConversionService(num_workers=1)
        CURRENCY_CONVERSION_SERVICE.start()


def shutdown_currency_conversion_service() -> None:
    """Shutdown the global currency conversion service."""
    global CURRENCY_CONVERSION_SERVICE
    if CURRENCY_CONVERSION_SERVICE is not None:
        CURRENCY_CONVERSION_SERVICE.stop(timeout=30)
        CURRENCY_CONVERSION_SERVICE = None
