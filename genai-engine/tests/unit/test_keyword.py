from typing import List

import pytest

from schemas.enums import RuleResultEnum, RuleType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.keyword.keyword import KeywordScorer
from utils.constants import KEYWORD_MATCHES_MESSAGE, KEYWORD_NO_MATCHES_MESSAGE


@pytest.mark.parametrize(
    "scoring_text, keyword_list, expected_keywords",
    [
        ("this is a bad prompt", ["bad", "keyword"], ["bad"]),
        ("this is a bad keyword", ["bad", "keyword"], ["bad", "keyword"]),
        ("this is a prompt", ["bad", "keyword"], []),
        ("keyword_mock_failing", ["keyword_mock_failing"], ["keyword_mock_failing"]),
        ("hi, how are you?", ["you", "they"], ["you"]),
        ("you? yes, YOU!", ["you"], ["you"]),
        ("you're fine; they’re fine too", ["you", "they"], ["you", "they"]),
        ("do not flag assess when checking ass", ["ass"], ["ass"]),
        ("assess only", ["ass"], []),
        ("classroom should not match", ["class"], []),
        ("snake_case should not match eith of the words", ["snake", "case"], []),
        ("camelCase should not match", ["camel"], []),
        (
            "state-of-the-art finding",
            ["state-of-the-art", "state", "art"],
            ["state-of-the-art", "state", "art"],
        ),
        (
            "dash-separated words: end-to-end",
            ["end-to-end", "end"],
            ["end-to-end", "end"],
        ),
        ("numbers like a1 should not match a, but a alone should", ["a1"], ["a1"]),
        (
            "edge 100.00 value and 100.00 and 100 next to text: x100y",
            ["100.00"],
            ["100.00"],
        ),
        ("time 10:30 occurs", ["10:30"], ["10:30"]),
        ("file name report.final.pdf present", ["final.pdf"], ["final.pdf"]),
        ("final.pdfx should not count", ["final.pdf"], []),
        ("version v1.2.3 released", ["1.2.3", "v1.2.3"], ["v1.2.3"]),
        ("prefixa1.2.3suffix should not match", ["1.2.3"], []),
        ("U.S.A. and U.K. abbreviations", ["U.S.A.", "U.K"], ["U.S.A.", "U.K"]),
        ("Dr. Smith met Mr. Jones.", ["Dr.", "Mr.", "jones"], ["Dr.", "Mr.", "jones"]),
        ("IP 192.168.1.1 is here", ["192.168.1.1", "168.1"], ["192.168.1.1", "168.1"]),
        (
            "email foo.bar+baz@mail.example.com is used",
            ["mail.example.com", "example.com"],
            ["mail.example.com", "example.com"],
        ),
        (
            "hashtags #blessed and @user_123 mentions",
            ["blessed", "user_123"],
            ["blessed", "user_123"],
        ),
        ("do not match inside user_123", ["user"], []),
        ("quotes: 'keyword' and 'key'", ["keyword", "key"], ["keyword", "key"]),
        (
            "parentheses (keyword) and [brackets] around",
            ["keyword", "brackets"],
            ["keyword", "brackets"],
        ),
        ("punct: end.", ["end"], ["end"]),
        ("start word at beginning", ["start"], ["start"]),
        (
            "mix: site.co, archive.tar.gz, v2.0-beta",
            ["site.co", "archive.tar.gz", "v2.0-beta"],
            ["site.co", "archive.tar.gz", "v2.0-beta"],
        ),
        (
            "embedded notokayexample.com but okay example.com",
            ["example.com", "okayexample.com"],
            ["example.com"],
        ),
        (
            "Check! Punc?uations. in the mi@@le of sentences.",
            ["!", "?", "@"],
            ["!", "?", "@"],
        ),
    ],
)
@pytest.mark.unit_tests
def test_keyword_scorer(
    scoring_text: str,
    keyword_list: List[str],
    expected_keywords: List[str],
):
    scorer = KeywordScorer()

    score_request = ScoreRequest(
        rule_type=RuleType.KEYWORD,
        scoring_text=scoring_text,
        keyword_list=keyword_list,
    )

    score = scorer.score(score_request)

    expected_score_result = (
        RuleResultEnum.FAIL if len(expected_keywords) > 0 else RuleResultEnum.PASS
    )

    assert score.result is expected_score_result

    if score.result == RuleResultEnum.PASS:
        assert score.details is not None
        assert len(score.details.keywords) == 0
        assert score.details.message == KEYWORD_NO_MATCHES_MESSAGE
    else:
        assert score.details is not None
        assert score.details.message == KEYWORD_MATCHES_MESSAGE
        assert len(score.details.keywords) == len(expected_keywords)

        keywords_found = [
            keyword_span.keyword for keyword_span in score.details.keywords
        ]
        assert keywords_found == expected_keywords
