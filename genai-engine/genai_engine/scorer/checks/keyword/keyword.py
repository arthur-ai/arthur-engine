import re

from schemas.enums import RuleResultEnum
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


class KeywordScorer(RuleScorer):
    def score(self, request: ScoreRequest) -> RuleScore:
        """checks if request contains any bad keywords"""
        text = request.scoring_text

        # split the response
        word_tokens = re.findall(r"[\w']+|[.,!?;]", text)
        word_tokens = [token.lower() for token in word_tokens]
        word_tokens = set(word_tokens)

        failed_keywords = []
        keyword_found = False
        for keyword in request.keyword_list:
            if keyword.lower() in word_tokens:
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
