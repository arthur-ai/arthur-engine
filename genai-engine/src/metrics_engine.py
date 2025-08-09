import concurrent.futures
import logging
import time
import uuid
from typing import List

from dotenv import load_dotenv
from opentelemetry import trace

from schemas.internal_schemas import Metric, MetricResult
from schemas.metric_schemas import MetricRequest
from scorer.score import ScorerClient
from utils import constants
from utils.metric_counters import METRIC_FAILURE_COUNTER
from utils.utils import TracedThreadPoolExecutor, get_env_var

tracer = trace.get_tracer(__name__)

load_dotenv()

logger = logging.getLogger(__name__)


class MetricsEngine:
    def __init__(self, scorer_client: ScorerClient):
        self.scorer_client = scorer_client

    def evaluate(
        self,
        request: MetricRequest,
        metrics: List[Metric],
    ) -> List[MetricResult]:
        if not metrics:
            return []
        metric_results = self.run_metrics(request, metrics)
        return metric_results

    @tracer.start_as_current_span("run metrics")
    def run_metrics(
        self,
        request: MetricRequest,
        metrics: List[Metric],
    ) -> List[MetricResult]:
        # Values: (Metric, run_metric_thread)
        thread_futures: list[tuple[Metric, concurrent.futures.Future]] = []
        num_threads = int(
            get_env_var(
                constants.GENAI_ENGINE_THREAD_POOL_MAX_WORKERS_ENV_VAR,
                default=str(constants.DEFAULT_THREAD_POOL_MAX_WORKERS),
            ),
        )
        with TracedThreadPoolExecutor(tracer, max_workers=num_threads) as executor:
            for metric in metrics:
                future = executor.submit(self.run_metric, request, metric)
                thread_futures.append((metric, future))
        metric_results: list[MetricResult] = []
        for metric, future in thread_futures:
            exc = future.exception()
            if exc is not None:
                logger.error(
                    "Metric evaluation failed. Metric: %s" % (metric.type),
                )
                logger.error(str(exc), exc_info=(type(exc), exc, exc.__traceback__))

                METRIC_FAILURE_COUNTER.add(1)
                metric_results.append(
                    MetricResult(
                        id=str(uuid.uuid4()),
                        metric_type=metric.type,
                        details=None,
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=0,
                        span_id=None,
                        metric_id=None,
                    ),
                )
            else:
                metric_results.append(future.result())
        return metric_results

    def run_metric(self, request: MetricRequest, metric: Metric):
        start_time = time.time()

        logger.info(f"Starting metric execution: {metric.type}")

        try:
            logger.debug(f"Running metric {metric.type}")
            score = self.scorer_client.score_metric(request, metric)
            logger.debug(f"Score: {score}")

            logger.info(f"Completed metric execution: {metric.type}")

        except Exception as e:
            logger.error(f"Error scoring metric {metric.type}: {str(e)}")
            raise e

        end_time = time.time()

        # Update the score with the correct id and latency
        score.id = str(uuid.uuid4())
        score.latency_ms = int((end_time - start_time) * 1000)

        return score
