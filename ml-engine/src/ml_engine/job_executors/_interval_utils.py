from datetime import timedelta

from arthur_client.api_bindings import AlertRuleInterval


def alert_interval_to_timedelta(interval: AlertRuleInterval) -> timedelta:
    return timedelta(**{interval.unit: interval.count})
