import re

from arthur_common.models.enums import RuleResultEnum
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerKeywordSpan,
    ScorerRuleDetails,
)
from scorer.scorer import RuleScorer
from utils import constants
from utils.token_count import TokenCounter

TOKEN_COUNTER = TokenCounter()


def is_punctuation_only(keyword: str) -> bool:
    # Returns True if the keyword has no letters, digits, or underscores
    return not re.search(r"\w", keyword)


def get_keyword_regex_pattern(keyword: str) -> str:
    escape_pattern = re.escape(keyword)

    if not is_punctuation_only(keyword):
        # if a keyword has word characters then use word-boundaries
        return rf"(?<!\w){escape_pattern}(?!\w)"

    return escape_pattern


class KeywordScorer(RuleScorer):
    def score(self, request: ScoreRequest) -> RuleScore:
        """checks if request contains any bad keywords"""
        text = request.scoring_text

        failed_keywords = []
        keyword_found = False
        for keyword in request.keyword_list:
            keyword_pattern = get_keyword_regex_pattern(keyword)

            if re.search(keyword_pattern, text, flags=re.IGNORECASE):
                failed_keywords.append(keyword)
                keyword_found = True

        reason = constants.KEYWORD_NO_MATCHES_MESSAGE
        if failed_keywords:
            reason = constants.KEYWORD_MATCHES_MESSAGE

        return RuleScore(
            result=RuleResultEnum.FAIL if keyword_found else RuleResultEnum.PASS,
            details=ScorerRuleDetails(
                message=reason,
                keywords=[ScorerKeywordSpan(keyword=k) for k in failed_keywords],
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
