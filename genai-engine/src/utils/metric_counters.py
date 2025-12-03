from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.types import Attributes

from utils.utils import get_env_var, new_relic_enabled

from . import constants

RULE_FAILURE_COUNTER = None
METRIC_FAILURE_COUNTER = None

if new_relic_enabled():
    service_name: str = get_env_var(constants.NEWRELIC_APP_NAME_ENV_VAR) or ""
    OTEL_RESOURCE_ATTRIBUTES: Attributes = {
        "service.name": service_name,
    }
    metrics.set_meter_provider(
        MeterProvider(
            resource=Resource.create(OTEL_RESOURCE_ATTRIBUTES),
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(),
                    export_interval_millis=60000.0,
                ),
            ],
        ),
    )

    RULE_FAILURE_COUNTER = metrics.get_meter(
        "opentelemetry.instrumentation.custom",
    ).create_counter(
        constants.NEWRELIC_CUSTOM_METRIC_RULE_FAILURES,
        unit="failures",
        description="Number of rule evaluation failures.",
    )

    METRIC_FAILURE_COUNTER = metrics.get_meter(
        "opentelemetry.instrumentation.custom",
    ).create_counter(
        constants.NEWRELIC_CUSTOM_METRIC_RULE_FAILURES,
        unit="failures",
        description="Number of metric evaluation failures.",
    )
