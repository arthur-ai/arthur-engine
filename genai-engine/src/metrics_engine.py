import concurrent.futures
import logging
import re
import time
from typing import List, Optional

from dotenv import load_dotenv
from opentelemetry import trace
from schemas.enums import MetricType
from schemas.internal_schemas import Metric
from schemas.metric_schemas import MetricRequest, MetricResult, MetricScore
from scorer.score import ScorerClient
from utils import constants
from utils.metric_counters import METRIC_FAILURE_COUNTER
from utils.token_count import TokenCounter
from utils.utils import TracedThreadPoolExecutor, get_env_var

tracer = trace.get_tracer(__name__)

load_dotenv()
# PROMPT_INJECTION_TOKEN_WARNING_LIMIT = 512
# MAX_SENSITIVE_DATA_TOKEN_LIMIT = int(
#     get_env_var(constants.GENAI_ENGINE_SENSITIVE_DATA_CHECK_MAX_TOKEN_LIMIT_ENV_VAR),
# )
# MAX_HALLUCINATION_TOKEN_LIMIT = int(
#     get_env_var(constants.GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT_ENV_VAR),
# )
# MAX_TOXICITY_TOKEN_LIMIT = int(
#     get_env_var(constants.GENAI_ENGINE_TOXICITY_CHECK_MAX_TOKEN_LIMIT_ENV_VAR, True)
#     or 1200,
# )

# ZERO_TOKEN_CONSUMPTION = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)

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
        with TracedThreadPoolExecutor(tracer) as executor:
            for metric in metrics:
                future = executor.submit(self.run_metric, request, metric)
                thread_futures.append((metric, future))
        metric_results: list[MetricResult] = []
        for metric, future in thread_futures:
            exc = future.exception()
            if exc is not None:
                logger.error(
                    "Metric evaluation failed. Metric ID: %s, Metric config: %s"
                    % (metric.id, metric.model_dump_json()),
                )
                logger.error(str(exc), exc_info=(type(exc), exc, exc.__traceback__))

                METRIC_FAILURE_COUNTER.add(1)
                metric_results.append(
                    MetricResult(
                        id=metric.id,
                        metric_score_result=MetricScore(
                            metric=metric.metric_type,
                            metric_details=None,
                            prompt_tokens=0,
                            completion_tokens=0,
                        ),
                        latency_ms=0,
                    ),
                )
            else:
                metric_results.append(future.result())
        return metric_results

    def run_metric(self, request: MetricRequest, metric: Metric):
        start_time = time.time()
        
        try:
            logger.debug(f"Running metric {metric.metric_type}")
            score = self.scorer_client.score_metric(request, metric)
            logger.debug(f"Score: {score}")
        except Exception as e:
            logger.error(f"Error scoring metric {metric.metric_type}: {str(e)}")
            raise e
            
        end_time = time.time()
        
        return MetricResult(
            id=metric.id,
            metric_score_result=score,
            latency_ms=int((end_time - start_time) * 1000)
        )

