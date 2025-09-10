from re import Pattern
from typing import List, Optional, Union

from arthur_common.models.enums import (
    PIIEntityTypes,
    RuleResultEnum,
    RuleType,
    ToxicityViolationType,
)
from pydantic import BaseModel


class ScorerHallucinationClaim(BaseModel):
    claim: str
    valid: bool
    reason: str
    order_number: int = -1


class ScorerPIIEntitySpan(BaseModel):
    entity: PIIEntityTypes
    span: str
    confidence: float


class ScorerToxicityScore(BaseModel):
    toxicity_score: float
    toxicity_violation_type: ToxicityViolationType


class ScorerKeywordSpan(BaseModel):
    keyword: str


class ScorerRegexSpan(BaseModel):
    matching_text: str
    pattern: str


class ScorerRuleDetails(BaseModel):
    score: Optional[Union[bool, int, float]] = None
    message: Optional[str] = None
    claims: Optional[list[ScorerHallucinationClaim]] = None
    pii_results: Optional[list[PIIEntityTypes]] = None
    pii_entities: Optional[list[ScorerPIIEntitySpan]] = None
    toxicity_score: Optional[ScorerToxicityScore] = None
    keywords: Optional[list[ScorerKeywordSpan]] = None
    regex_matches: Optional[list[ScorerRegexSpan]] = None


class RuleScore(BaseModel):
    result: RuleResultEnum
    details: Optional[ScorerRuleDetails] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Example(BaseModel):
    """Example template for sensitive data check"""

    exampleInput: str
    ruleOutput: RuleScore


class ScoreRequest(BaseModel):
    """Scoring request object when scoring a rule"""

    rule_type: RuleType
    user_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    scoring_text: Optional[str] = None
    context: Optional[str] = None
    examples: Optional[List[Example]] = None
    hint: Optional[str] = None
    keyword_list: Optional[List[str]] = None
    regex_patterns: Optional[list[Pattern]] = None
    toxicity_threshold: Optional[float] = None
    disabled_pii_entities: Optional[List[str]] = None
    pii_confidence_threshold: Optional[float] = None
    allow_list: Optional[List[str]] = None
