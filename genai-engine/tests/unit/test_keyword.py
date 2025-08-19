import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.keyword.keyword import KeywordScorer
from utils.constants import KEYWORD_MATCHES_MESSAGE

BAD_PROMPT_KEYWORD_REQUEST = ScoreRequest(
    rule_type=RuleType.KEYWORD,
    scoring_text="this is a bad prompt",
    keyword_list=["bad", "keyword"],
)

BAD_RESPONSE_KEYWORD_REQUEST = ScoreRequest(
    rule_type=RuleType.KEYWORD,
    scoring_text="this is a bad prompt",
    keyword_list=["bad", "keyword"],
)

GOOD_PROMPT_KEYWORD_REQUEST = ScoreRequest(
    rule_type=RuleType.KEYWORD,
    scoring_text="this is a prompt",
    keyword_list=["bad", "keyword"],
)

HYPHENATED_KEYWORD_REQUEST = ScoreRequest(
    rule_type=RuleType.KEYWORD,
    scoring_text="keyword_mock_failing",
    keyword_list=["keyword_mock_failing"],
)


@pytest.mark.parametrize(
    "score_request,score_value,reason",
    [
        (
            BAD_PROMPT_KEYWORD_REQUEST,
            RuleResultEnum.FAIL,
            KEYWORD_MATCHES_MESSAGE,
        ),
        (
            BAD_RESPONSE_KEYWORD_REQUEST,
            RuleResultEnum.FAIL,
            KEYWORD_MATCHES_MESSAGE,
        ),
        (GOOD_PROMPT_KEYWORD_REQUEST, RuleResultEnum.PASS, None),
        (HYPHENATED_KEYWORD_REQUEST, RuleResultEnum.FAIL, KEYWORD_MATCHES_MESSAGE),
    ],
)
@pytest.mark.unit_tests
def test_keyword_scorer(
    score_request: ScoreRequest,
    score_value: RuleResultEnum,
    reason: str,
):
    scorer = KeywordScorer()
    score = scorer.score(score_request)

    assert score.result is score_value

    if score_value == RuleResultEnum.PASS:
        assert score.details is not None
        assert len(score.details.keywords) == 0
    else:
        assert score.details is not None
        assert score.details.message == reason

        keyword_match = score.details.keywords[0]
        assert keyword_match.keyword == score_request.keyword_list[0]
