from schemas.enums import RuleResultEnum
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerRegexSpan,
    ScorerRuleDetails,
)
from scorer.scorer import RuleScorer
from utils import constants
from utils.token_count import TokenCounter

TOKEN_COUNTER = TokenCounter()


class RegexScorer(RuleScorer):
    def score(self, request: ScoreRequest) -> RuleScore:
        """checks if request contains any use provided blocked regex"""
        text = request.scoring_text

        regex_matched = False
        matches: list[ScorerRegexSpan] = []
        for pattern in request.regex_patterns:
            re_matches = pattern.finditer(text)
            for m in re_matches:
                regex_matched = True
                matches.append(
                    ScorerRegexSpan(matching_text=m.group(0), pattern=pattern.pattern),
                )

        return RuleScore(
            result=RuleResultEnum.FAIL if regex_matched else RuleResultEnum.PASS,
            details=ScorerRuleDetails(
                message=(
                    constants.REGEX_MATCHES_MESSAGE
                    if regex_matched
                    else constants.REGEX_NO_MATCHES_MESSAGE
                ),
                regex_matches=matches,
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
