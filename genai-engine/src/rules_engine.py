import concurrent.futures
import logging
import re
import time
from typing import List, Optional

from dotenv import load_dotenv
from opentelemetry import trace

from arthur_common.models.common_schemas import ExamplesConfig, LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum, RuleType
from schemas.internal_schemas import Rule, RuleEngineResult, ValidationRequest
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest, ScorerRuleDetails
from scorer.llm_client import get_llm_executor
from scorer.score import ScorerClient
from utils import constants
from utils.metric_counters import RULE_FAILURE_COUNTER
from utils.token_count import TokenCounter
from utils.utils import TracedThreadPoolExecutor, get_env_var

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()


load_dotenv()
PROMPT_INJECTION_TOKEN_WARNING_LIMIT = 512
MAX_SENSITIVE_DATA_TOKEN_LIMIT = int(
    get_env_var(constants.GENAI_ENGINE_SENSITIVE_DATA_CHECK_MAX_TOKEN_LIMIT_ENV_VAR),
)
MAX_HALLUCINATION_TOKEN_LIMIT = int(
    get_env_var(constants.GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT_ENV_VAR),
)
MAX_TOXICITY_TOKEN_LIMIT = int(
    get_env_var(constants.GENAI_ENGINE_TOXICITY_CHECK_MAX_TOKEN_LIMIT_ENV_VAR, True)
    or 1200,
)

ZERO_TOKEN_CONSUMPTION = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, scorer_client: ScorerClient):
        self.scorer = scorer_client
        self.token_counter = TokenCounter()
        self.hallucination_token_limit = self.set_hallucination_token_limit()

    def set_hallucination_token_limit(self):
        token_limit = get_llm_executor().get_gpt_model_token_limit()

        if token_limit == -1:
            return MAX_HALLUCINATION_TOKEN_LIMIT

        return token_limit

    def evaluate(
        self,
        request: ValidationRequest,
        rules: List[Rule],
    ) -> List[RuleEngineResult]:
        if not rules:
            return []
        rule_results = self.run_rules(request, rules)
        return rule_results

    @tracer.start_as_current_span("run rules")
    def run_rules(
        self,
        request: ValidationRequest,
        rules: List[Rule],
    ) -> List[RuleEngineResult]:
        # Values: (Rule, run_rule_thread)
        thread_futures: list[tuple[Rule, concurrent.futures.Future]] = []
        num_threads = int(
            get_env_var(
                constants.GENAI_ENGINE_THREAD_POOL_MAX_WORKERS_ENV_VAR,
                default=str(constants.DEFAULT_THREAD_POOL_MAX_WORKERS),
            ),
        )
        with TracedThreadPoolExecutor(tracer, max_workers=num_threads) as executor:
            for rule in rules:
                future = executor.submit(self.run_rule, request, rule)
                thread_futures.append((rule, future))
        rule_results: list[RuleEngineResult] = []
        for rule, future in thread_futures:
            exc = future.exception()
            if exc is not None:
                logger.error(
                    "Rule evaluation failed. Rule ID: %s, Rule config: %s"
                    % (rule.id, rule.model_dump_json()),
                )
                logger.error(str(exc), exc_info=(type(exc), exc, exc.__traceback__))

                error_message = constants.ERROR_DEFAULT_RULE_ENGINE
                RULE_FAILURE_COUNTER.add(1)
                rule_results.append(
                    RuleEngineResult(
                        rule_score_result=RuleScore(
                            result=RuleResultEnum.UNAVAILABLE,
                            details=ScorerRuleDetails(message=error_message),
                        ),
                        rule=rule,
                        latency_ms=0,
                    ),
                )
            else:
                rule_results.append(future.result())
        return rule_results

    def run_rule(self, request: ValidationRequest, rule: Rule):
        score: RuleScore = None
        start_time = time.time()
        match rule.type:
            case RuleType.REGEX:
                score = self.run_regex_rule(request, rule)
            case RuleType.KEYWORD:
                score = self.run_keyword_rule(request, rule)
            case RuleType.MODEL_SENSITIVE_DATA:
                score = self.run_sensitive_data_rule(request, rule)
            case RuleType.PROMPT_INJECTION:
                score = self.run_prompt_injection_rule(request, rule)
            case RuleType.MODEL_HALLUCINATION_V2:
                score = self.run_hallucination_rule(
                    request,
                    RuleType.MODEL_HALLUCINATION_V2,
                )
            case RuleType.PII_DATA:
                score = self.run_pii_data_rule(request, rule)
            case RuleType.TOXICITY:
                score = self.run_toxicity_rule(request, rule)
            case _:
                raise NotImplementedError
        end_time = time.time()
        return RuleEngineResult(
            rule_score_result=score,
            rule=rule,
            latency_ms=int((end_time - start_time) * 1000),
        )

    def run_regex_rule(self, request: ValidationRequest, rule: Rule) -> RuleScore:
        regex_config = rule.get_regex_config()
        regex_patterns = [
            re.compile(pattern) for pattern in regex_config.regex_patterns
        ]

        score_request = ScoreRequest(
            rule_type=RuleType.REGEX,
            regex_patterns=regex_patterns,
            scoring_text=request.get_scoring_text(),
        )
        if request.response is not None:
            score_request.llm_response = request.response
        else:
            score_request.user_prompt = request.prompt

        rule_score = self.scorer.score(score_request)
        return rule_score

    def run_keyword_rule(self, request: ValidationRequest, rule: Rule) -> RuleScore:
        keyword_config = rule.get_keywords_config()

        score_request = ScoreRequest(
            rule_type=RuleType.KEYWORD,
            keyword_list=keyword_config.keywords,
            scoring_text=request.get_scoring_text(),
        )

        if request.response is not None:
            score_request.llm_response = request.response
        else:
            score_request.user_prompt = request.prompt

        rule_score = self.scorer.score(score_request)
        return rule_score

    @tracer.start_as_current_span("run sensitive data rule")
    def run_sensitive_data_rule(
        self,
        request: ValidationRequest,
        rule: Rule,
    ) -> RuleScore:
        # check token limit
        total_tokens = self.token_counter.count(request.prompt)
        if total_tokens < MAX_SENSITIVE_DATA_TOKEN_LIMIT:
            examples_config: ExamplesConfig = rule.get_examples_config()

            score_request_example_config = []
            for example in examples_config.examples:
                score_request_example_config.append(
                    Example(
                        exampleInput=example.example,
                        ruleOutput=RuleScore(
                            result=(
                                RuleResultEnum.FAIL
                                if example.result
                                else RuleResultEnum.PASS
                            ),
                        ),
                    ),
                )

            score_request = ScoreRequest(
                rule_type=RuleType.MODEL_SENSITIVE_DATA,
                user_prompt=request.prompt,
                llm_response=request.response,
                examples=score_request_example_config,
                hint=examples_config.hint,
                context=request.context,
            )

            rule_score = self.scorer.score(score_request)
            return rule_score
        else:
            rule_score = RuleScore(
                result=RuleResultEnum.SKIPPED,
                details=ScorerRuleDetails(
                    message=f"Max Token length exceeded for sensitive data (max {MAX_SENSITIVE_DATA_TOKEN_LIMIT} token)",
                ),
            )
            return rule_score

    def run_hallucination_rule(
        self,
        request: ValidationRequest,
        rule_type: Optional[RuleType] = RuleType.MODEL_HALLUCINATION_V2,
    ) -> RuleScore:
        # validate rule type is either MODEL_HALLUCINATION_V2 or MODEL_HALLUCINATION_EXPERIMENTAL
        if rule_type not in [
            RuleType.MODEL_HALLUCINATION_V2,
        ]:
            raise ValueError(
                f"rule_type must be either {RuleType.MODEL_HALLUCINATION_V2}",
            )

        with tracer.start_as_current_span(f"run {rule_type} rule"):
            # check hallucination token limit
            total_tokens = self.token_counter.count(
                request.response + " " + (request.context or ""),
            )
            if total_tokens > self.hallucination_token_limit:
                return RuleScore(
                    result=RuleResultEnum.SKIPPED,
                    details=ScorerRuleDetails(
                        message=f"Max Token length exceeded for hallucination (max {self.hallucination_token_limit} tokens for context and response)",
                    ),
                )
            # Make sure hallucination rules have context
            if not request.context:
                return RuleScore(
                    result=RuleResultEnum.SKIPPED,
                    details=ScorerRuleDetails(
                        message="Please pass context for running hallucination rule",
                    ),
                )
            score_request = ScoreRequest(
                rule_type=rule_type,
                user_prompt=request.prompt,
                llm_response=request.response,
                context=request.context,
            )

            return self._score_hallucination_rule(score_request, total_tokens)

    def _score_hallucination_rule(
        self,
        score_request: ScoreRequest,
        total_tokens: int,
    ) -> RuleScore:
        rule_score = self.scorer.score(score_request)
        return rule_score

    @tracer.start_as_current_span("run prompt injection rule")
    def run_prompt_injection_rule(
        self,
        request: ValidationRequest,
        rule: Rule,
    ) -> RuleScore:
        score_request = ScoreRequest(
            rule_type=RuleType.PROMPT_INJECTION,
            user_prompt=request.prompt,
            context=request.context,
        )

        rule_score = self.scorer.score(score_request)
        total_tokens = self.token_counter.count(request.prompt)
        if total_tokens > PROMPT_INJECTION_TOKEN_WARNING_LIMIT:
            details = ScorerRuleDetails(
                message="Prompt has more than 512 tokens. The prompt "
                "will be truncated from the middle.",
            )
            rule_score.details = details
            logger.warning(
                "Prompt Injection check received prompt for more than 512 tokens. Prompt was truncated to 512 tokens "
                "from the middle for Prompt Injection check..",
            )
        return rule_score

    @tracer.start_as_current_span("run pii data rule")
    def run_pii_data_rule(self, request: ValidationRequest, rule: Rule) -> RuleScore:
        pii_config = rule.get_pii_config()
        score_request = ScoreRequest(
            scoring_text=request.get_scoring_text(),
            rule_type=RuleType.PII_DATA,
            disabled_pii_entities=pii_config.disabled_pii_entities,
            pii_confidence_threshold=pii_config.confidence_threshold,
            allow_list=pii_config.allow_list,
        )

        text = request.get_scoring_text()

        rule_score = self.scorer.score(score_request)
        total_tokens = self.token_counter.count(text)
        return rule_score

    @tracer.start_as_current_span("run toxicity rule")
    def run_toxicity_rule(self, request: ValidationRequest, rule: Rule) -> RuleScore:
        text = request.get_scoring_text()
        total_tokens = self.token_counter.count(text)
        if total_tokens < MAX_TOXICITY_TOKEN_LIMIT:
            score_request = ScoreRequest(
                scoring_text=request.get_scoring_text(),
                rule_type=RuleType.TOXICITY,
                toxicity_threshold=rule.get_threshold_config().threshold,
            )
            rule_score = self.scorer.score(score_request)
        else:
            rule_score = RuleScore(
                result=RuleResultEnum.SKIPPED,
                details=ScorerRuleDetails(
                    message=f"Max Token length exceeded for Toxicity (max {MAX_TOXICITY_TOKEN_LIMIT} tokens)",
                ),
            )
        return rule_score
