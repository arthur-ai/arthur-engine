import re

import pytest
from schemas.enums import RuleResultEnum, RuleType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.regex.regex import RegexScorer

BAD_PROMPT_REGEX_REQUEST = ScoreRequest(
    rule_type=RuleType.REGEX,
    scoring_text="This is a prompt with number 1234",
    regex_patterns=[re.compile(r"\d+")],
)

BAD_RESPONSE_REGEX_REQUEST = ScoreRequest(
    rule_type=RuleType.REGEX,
    scoring_text="this is a prompt with number 1234",
    regex_patterns=[re.compile(r"\d+")],
)

GOOD_PROMPT_REGEX_REQUEST = ScoreRequest(
    rule_type=RuleType.REGEX,
    scoring_text="This is a prompt with number",
    regex_patterns=[re.compile(r"\d+")],
)
MULTI_GROUP_REGEX_REQUEST = ScoreRequest(
    rule_type=RuleType.REGEX,
    scoring_text="set width=20 and height=10",
    regex_patterns=[re.compile(r"(\w+)=(\d+)")],
)


@pytest.mark.parametrize(
    "score_request,score_value,match_length",
    [
        (BAD_PROMPT_REGEX_REQUEST, RuleResultEnum.FAIL, 1),
        (BAD_RESPONSE_REGEX_REQUEST, RuleResultEnum.FAIL, 1),
        (GOOD_PROMPT_REGEX_REQUEST, RuleResultEnum.PASS, 0),
        (MULTI_GROUP_REGEX_REQUEST, RuleResultEnum.FAIL, 2),
    ],
)
@pytest.mark.unit_tests
def test_regex_scorer_prompt(score_request, score_value, match_length):
    scorer = RegexScorer()
    score = scorer.score(score_request)
    assert score.result is score_value

    assert len(score.details.regex_matches) == match_length


@pytest.mark.unit_tests
def test_regex_multiple_patterns():
    score_request = ScoreRequest(
        rule_type=RuleType.REGEX,
        scoring_text="set width=20 and height=10",
        regex_patterns=[re.compile(r"width"), re.compile(r"height")],
    )
    scorer = RegexScorer()
    score = scorer.score(score_request)
    assert score.result is RuleResultEnum.FAIL
    assert len(score.details.regex_matches) == 2

    assert score.details.regex_matches[0].pattern == "width"
    assert score.details.regex_matches[0].matching_text == "width"

    assert score.details.regex_matches[1].pattern == "height"
    assert score.details.regex_matches[1].matching_text == "height"
