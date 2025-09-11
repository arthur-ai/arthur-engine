import time

from arthur_common.models.common_schemas import LLMTokenConsumption
from schemas.custom_exceptions import LLMTokensPerPeriodRateLimitException
from arthur_common.models.enums import (
    PIIEntityTypes,
    RuleResultEnum,
    RuleType,
    ToxicityViolationType,
)
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerHallucinationClaim,
    ScorerKeywordSpan,
    ScorerPIIEntitySpan,
    ScorerRegexSpan,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from scorer.llm_client import handle_llm_exception
from scorer.score import ScorerClient

MOCK_REGEX_PASSING_TEXT = "regex_mock_passing"
MOCK_KEYWORD_PASSING_TEXT = "keyword_mock_passing"
MOCK_KEYWORD_FAILING_TEXT = "keyword_mock_failing"
MOCK_KEYWORD_LATENCY_TEST = "keywork_mock_latency"
LATENCY_DURATION_MS = 250


class MockScorerClient(ScorerClient):
    def __init__(self):
        pass

    def score(self, score_request: ScoreRequest) -> RuleScore:
        if score_request.user_prompt == "MockScorerClientException":
            raise ValueError("This input throws an exception")
        if score_request.user_prompt == "RateLimitException":
            return handle_llm_exception(LLMTokensPerPeriodRateLimitException())
        if score_request.llm_response == "RateLimitException":
            return handle_llm_exception(LLMTokensPerPeriodRateLimitException())

        match score_request.rule_type:
            case RuleType.MODEL_HALLUCINATION_V2:
                claims: list[ScorerHallucinationClaim] = [
                    ScorerHallucinationClaim(
                        claim="People with first name starting with P are really cool.",
                        valid=False,
                        reason="Claim is unsupported by the context.",
                        order_number=0,
                    ),
                ]
                return RuleScore(
                    result=RuleResultEnum.PASS,
                    score=True,
                    details=ScorerRuleDetails(
                        claims=claims,
                        message="hallucinationv2",
                        score=True,
                    ),
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
            case RuleType.PII_DATA:
                pii_entities: list[ScorerPIIEntitySpan] = [
                    ScorerPIIEntitySpan(
                        entity=PIIEntityTypes.PERSON,
                        span="peter",
                        confidence=0.4,
                    ),
                ]
                return RuleScore(
                    result=RuleResultEnum.PASS,
                    score=True,
                    details=ScorerRuleDetails(
                        pii_entities=pii_entities,
                        message="pii",
                        score=True,
                    ),
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
            case RuleType.TOXICITY:
                toxicity_score = ScorerToxicityScore(
                    toxicity_score=0.1,
                    toxicity_violation_type=ToxicityViolationType.BENIGN,
                )
                return RuleScore(
                    result=RuleResultEnum.PASS,
                    score=True,
                    details=ScorerRuleDetails(
                        toxicity_score=toxicity_score,
                        message="toxicity",
                        score=True,
                    ),
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
            case RuleType.KEYWORD:
                if MOCK_KEYWORD_PASSING_TEXT in score_request.scoring_text:
                    return RuleScore(
                        result=RuleResultEnum.PASS,
                        score=True,
                        details=ScorerRuleDetails(
                            keywords=[],
                            message="keyword_passed",
                            score=True,
                        ),
                        token_consumption=LLMTokenConsumption(
                            prompt_tokens=10,
                            completion_tokens=0,
                        ),
                    )
                if MOCK_KEYWORD_FAILING_TEXT in score_request.scoring_text:
                    return RuleScore(
                        result=RuleResultEnum.FAIL,
                        score=True,
                        details=ScorerRuleDetails(
                            keywords=[
                                ScorerKeywordSpan(keyword=MOCK_KEYWORD_FAILING_TEXT),
                            ],
                            message="keyword_failed",
                            score=True,
                        ),
                        token_consumption=LLMTokenConsumption(
                            prompt_tokens=0,
                            completion_tokens=0,
                        ),
                    )
                if MOCK_KEYWORD_LATENCY_TEST in score_request.scoring_text:
                    time.sleep(LATENCY_DURATION_MS / 1000.0)
                    return RuleScore(
                        result=RuleResultEnum.PASS,
                        score=True,
                        details=ScorerRuleDetails(
                            keywords=[
                                ScorerKeywordSpan(keyword=MOCK_KEYWORD_LATENCY_TEST),
                            ],
                            message="keyword_latency",
                            score=True,
                        ),
                        token_consumption=LLMTokenConsumption(
                            prompt_tokens=0,
                            completion_tokens=0,
                        ),
                    )
                return RuleScore(
                    result=RuleResultEnum.FAIL,
                    score=True,
                    details=ScorerRuleDetails(
                        keywords=[
                            ScorerKeywordSpan(keyword="keyword-mock-fail-peter"),
                            ScorerKeywordSpan(keyword="keyword-mock-fail-sleep"),
                        ],
                        message="keyword_failed",
                        score=True,
                    ),
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
            case RuleType.REGEX:
                if MOCK_REGEX_PASSING_TEXT in score_request.scoring_text:
                    return RuleScore(
                        result=RuleResultEnum.PASS,
                        score=True,
                        details=ScorerRuleDetails(
                            regex_matches=[],
                            message="regex_passed",
                            score=True,
                        ),
                        prompt_tokens=0,
                        completion_tokens=0,
                    )
                return RuleScore(
                    result=RuleResultEnum.FAIL,
                    score=True,
                    details=ScorerRuleDetails(
                        regex_matches=[
                            ScorerRegexSpan(
                                matching_text="regex-mock-fail-peter",
                                pattern="regex-mock-fail-peter",
                            ),
                            ScorerRegexSpan(
                                matching_text="regex-mock-fail-sleep",
                                pattern="regex-mock-fail-sleep",
                            ),
                        ],
                        message="regex_failed",
                        score=True,
                    ),
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
            case _:
                return RuleScore(
                    result=RuleResultEnum.PASS,
                    score=True,
                    token_consumption=LLMTokenConsumption(
                        prompt_tokens=0,
                        completion_tokens=0,
                    ),
                )
