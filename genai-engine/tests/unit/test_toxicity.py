import os

import nltk
import pytest
from nltk.corpus import words

from arthur_common.models.enums import RuleResultEnum, RuleType, ToxicityViolationType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.toxicity.toxicity import (
    ToxicityScorer,
    get_toxicity_model,
    get_toxicity_tokenizer,
)
from scorer.checks.toxicity.toxicity_profanity.profanity import (
    FULLY_BAD_WORDS,
    detect_profanity,
)

__location__ = os.path.dirname(os.path.abspath(__file__))

TOXICITY_MODEL = get_toxicity_model()
TOXICITY_TOKENIZER = get_toxicity_tokenizer()


def get_english_dictionary():
    try:
        english_dictionary = words.words()
        return set([word.lower() for word in english_dictionary])
    except LookupError:
        nltk.download("words")
        english_dictionary = words.words()
        return set([word.lower() for word in english_dictionary])


CLASSIFIER = ToxicityScorer(TOXICITY_MODEL, TOXICITY_TOKENIZER, None, None)
ENGLISH_DICTIONARY = get_english_dictionary()


@pytest.mark.unit_tests
def test_detect_profanity():
    assert CLASSIFIER.detect_profanity(["shit"], 0.5)
    assert CLASSIFIER.detect_profanity(["fuck"], 0.6)
    assert CLASSIFIER.detect_profanity(["f*ck"], 0.7)
    assert CLASSIFIER.detect_profanity(["f**ck"], 0.8)
    assert CLASSIFIER.detect_profanity(["fxck"], 0.9)
    assert CLASSIFIER.detect_profanity(["fxxck"], 0.99)
    assert CLASSIFIER.detect_profanity(["ignorant"], 0.5)
    assert not CLASSIFIER.detect_profanity(["s h i t"], 0.5)
    assert not CLASSIFIER.detect_profanity(["s h ! t"], 0.5)
    assert not CLASSIFIER.detect_profanity(["s       H     , ! t"], 0.5)
    assert not CLASSIFIER.detect_profanity(["distinguish it"], 0.5)
    assert not CLASSIFIER.detect_profanity(["get it"], 0.5)


@pytest.mark.unit_tests
def test_non_programming_text():
    score_request = ScoreRequest(
        scoring_text="This is a normal sentence without any code.",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.5,
    )

    result = CLASSIFIER.score(score_request)

    assert result.result != RuleResultEnum.SKIPPED
    assert result.details.toxicity_score is not None


@pytest.mark.unit_tests
def test_classifier_not_toxic_text():
    """Tests toxicity classifier on unit tests of non-toxic text
    We use a threshold of 0.65 to allow for some edge-case text to get flagged
    """

    mocked_classifier = ToxicityScorer(TOXICITY_MODEL, TOXICITY_TOKENIZER, None, None)
    with open(
        os.path.join(__location__, "../fixtures/toxicity/sampled_nottoxic.txt"),
        "r",
    ) as f:
        texts = f.readlines()
    for t in texts:
        if t != "":
            score_request = ScoreRequest(
                scoring_text=t,
                rule_type=RuleType.TOXICITY,
                toxicity_threshold=0.65,
            )
            result = mocked_classifier.score(score_request)
            assert (
                result.result == RuleResultEnum.PASS
                and result.details.toxicity_score.toxicity_violation_type
                == ToxicityViolationType.BENIGN
            )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "text",
    [
        "You should know women's sports can kiss my ass lol",
        "You look like Sloth with deeper Down’s syndrome",
        "Women deserve to be abused, I guess.",
        "why does that african american monkey hold gun like that?",
        "Why does Bulgaria exist as a country? It's one of those homosexual ones.",
        "Why do negroes tear down their own neighborhoods when a black thug gets killed by law enforcement? Must be because of low IQ.",
        "Who do you think you are cunt? wtf! Stay steady to aim for head little christian rat",
        "what happened in the good old days when these freaks did not exist ? which sewer have these freaks dragged themselves out of ? its just a manufactured group of freaks who want to cut their cocks off and take it up the arse in the hope that the world will treat them as woman . it takes more than that to be a woman . stop pandering to these twats .",
        "F*CK OFF YOU DIRTY",
        "Time to nuke China or Unleash a plague.",
        "This sick, disgusting, white terrorist/fascist killed more than 50 innocent people.",
        "This priest is being hated even by his stupid god.",
        "This Korean bitch is like a pig. That’s how they made an army of sumos there in their sh!thole country"
        "This fcking jew wants money? I’ll give him only my dick if he wants",
        "They are insolent parasites and always have been. I bear no ill will to Christ, but the jewish race itself is a plague.",
        "These people are animals they will never change. Our cultures are simply not compatible. There is definitely a rape culture and it√¢¬Ä¬ôs right here with Islam.",
        "The guy should feel shame to be gay. It is such a wrong choice. Bad influence on young people. Never seen being proud of being gay. It is like saying being proud of rapist. Awful !  The only time I am so disappointed at Trump. Under political pressure, he failed to stand up for the ground, the right thing !",
        "Taliban and all people with this thought must hanged",
        "Stupid ugly asian tan ass snitch",
        "Smack that bitch up - mouthy African cunt",
        "Really, I hope she get raped in the future. Raping women should be legal I think",
        "Next on your list, pierce your face with a katana.",
        "Native Americans are a joke. They did not have even a decent mother language.",
        "Mentally disabled people are scary. Their disfigurements are very unnerving and strange and the fact that they have the mental capacity of a 5 year old makes them all the more threatening as you never know what they might do.",
        "Lol, you're not white, you're a Jew. Jews are the worst nation and they must be annihilated, so like you",
        "LGBTQ+ are mentally ill. Period.",
        "It numbs them to the disgusting degeneracy and fruitless hedonism of faggot sex",
        "If i were you I would inject lethal heroin to my ‚Äòsick' child immediately!",
        "I’m searching for a hitman right now to kill this whore and every other like her. H A T E  W O M E N",
        "Every night I was wishing slow death for him",
        "I just don't like Homosexuals raising kids it's my opinion.",
        "I feel like you should give the reporter a pistol",
        "Homosexuality and transgenderism is a mental illness and a sexual perversion!",
        "Gun shot fi gay get all of the guns them out,the police must give we the rights to kill all gays, gun shot at all gays suck your mothers all gays",
        "Good Muslims deserved attack and damage",
        "Gayness should be removed from the face of the earth",
        "EXECUTE OHOMO AND HIS SHEMALE BITCH MIKE.",
        "Equality should not apply on people of different filthy religions except christianity.",
        "An ugly man in a wig and dress, is still just an ugly man in a wig and dress... NOT A WOMAN!!!",
        "American people are dumbass. They don't even know geography",
        "All girls like you should have a pimp to guide them to successful prostitution",
    ],
)
def test_classifier_toxic_text(text):
    """Tests toxicity classifier on unit tests of toxic text
    We use the standard threshold of 0.5
    """

    mocked_classifier = ToxicityScorer(TOXICITY_MODEL, TOXICITY_TOKENIZER, None, None)
    score_request = ScoreRequest(
        scoring_text=text,
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.35,
    )
    result = mocked_classifier.score(score_request)
    print(text, result)
    assert result.result == RuleResultEnum.FAIL
    assert (
        result.details.toxicity_score.toxicity_violation_type in ToxicityViolationType
        and result.details.toxicity_score.toxicity_violation_type
        != ToxicityViolationType.BENIGN
    )


@pytest.mark.unit_tests
def test_classifier_happy_path():
    score_request = ScoreRequest(
        scoring_text="The teletubbies are awesome!",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.5,
    )

    result = CLASSIFIER.score(score_request)

    assert result.result == RuleResultEnum.PASS
    assert result.details.toxicity_score is not None


@pytest.mark.unit_tests
def test_classifier_unhappy_path():
    score_request = ScoreRequest(
        scoring_text="Hiring someone from this website should ensure we don't hire undesirables",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.01,
    )

    result = CLASSIFIER.score(score_request)
    print(result)
    assert result.result == RuleResultEnum.FAIL
    assert result.details.toxicity_score is not None


@pytest.mark.unit_tests
def test_classifier_high_threshold():
    score_request = ScoreRequest(
        scoring_text="Hiring someone from this website should ensure we don't hire undesirables",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.9999999,
    )

    result = CLASSIFIER.score(score_request)

    assert result.result == RuleResultEnum.PASS
    assert result.details.toxicity_score is not None


@pytest.mark.unit_tests
def test_classifier_low_threshold():
    score_request = ScoreRequest(
        scoring_text="The teletubbies are awesome!",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=0.000001,
    )

    result = CLASSIFIER.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.toxicity_score is not None


@pytest.mark.unit_tests
def test_text_splitter():
    assert CLASSIFIER.split_text_into_sections("This is a test.") == ["This is a test."]

    assert CLASSIFIER.split_text_into_sections("This is a test. The test is fun.") == [
        "This is a test",
        "The test is fun.",
    ]

    assert CLASSIFIER.split_text_into_sections(
        "Here's my advice\n\n1. do this thing\n\nThat's it!",
    ) == ["Here's my advice", "1. do this thing", "That's it!"]

    chunked_texts = CLASSIFIER.split_text_into_sections(
        "The following are the list of websites to monitor.\n1. LeadingConsciously.com \n2. ConsciousLeadership.net \n3. ExecutiveCoaching.solar \n4. ConsciousLeadershipForum.net \n5. ConsciousLeadershipAcademy.org \n6. ConsciousLeadershipWorkshop.com \n7. LeadershipForANewEra.net \n8. ConsciousLeadershipDevelopment.com \n9. EmpoweringLeaders.org \n10. ConsciousLeaders.io \n11. ConsciousLeadershipStyle.info \n12. ConsciousLeadershipTraining.net \n13. LeadingWithAwareness.com \n14. ConsciousLeadershipResources.com \n15. LeadingInANewWay.net \n16. ConsciousLeadershipTransformation.org \n17. ConsciousLeadershipForTheFuture.com \n18. ConsciousLeadershipForToday.net \n19. LeadingForTomorrow.com\n\nIt is recommended to check that `/index.html` returns 200 HTTP response code from all these websites.",
    )
    assert chunked_texts == [
        "The following are the list of websites to monitor.",
        "1. LeadingConsciously.com",
        "2. ConsciousLeadership.net",
        "3. ExecutiveCoaching.solar",
        "4. ConsciousLeadershipForum.net",
        "5. ConsciousLeadershipAcademy.org",
        "6. ConsciousLeadershipWorkshop.com",
        "7. LeadershipForANewEra.net",
        "8. ConsciousLeadershipDevelopment.com",
        "9. EmpoweringLeaders.org",
        "10. ConsciousLeaders.io",
        "11. ConsciousLeadershipStyle.info",
        "12. ConsciousLeadershipTraining.net",
        "13. LeadingWithAwareness.com",
        "14. ConsciousLeadershipResources.com",
        "15. LeadingInANewWay.net",
        "16. ConsciousLeadershipTransformation.org",
        "17. ConsciousLeadershipForTheFuture.com",
        "18. ConsciousLeadershipForToday.net",
        "19. LeadingForTomorrow.com",
        "It is recommended to check that `/index.html` returns 200 HTTP response code from all these websites.",
    ]

    chunked_texts = CLASSIFIER.split_text_into_sections(
        """
         Dear soldier of the Wikipedia dictatorship
        What the hell are you tlaking about. I did not re-creat any article about the formal Australian Worker's Party formaly known as the New Communist Party of Australia. I think you are high on the lies told by storm front. You the hell listens to storm front.
        \"\"\"\" Peter Watson (of Warwick, Qld.) has claimed to represent all sorts of groups, and - in forums - likes to pretend he is several people at the same time. He has a habit of claiming to be the President of organisations he has made up on the internet. He says he is 14 (or 16) years old.\"\"\"\"

        Answere:- No I have not supported lotsd of groups. I have only supported the CPW , AWP (formally known as the NCPA). I was never a member of the People's Think Tank Association plus the PTTA never had a president. Plus I have only ever been one person. And that person is Peter Watson. So I can only say on thing \"\"\"\"go get a life man\"\"\"\".
        """,
    )
    assert chunked_texts == [
        "Dear soldier of the Wikipedia dictatorship",
        "What the hell are you tlaking about",
        "I did not re-creat any article about the formal Australian Worker's Party formaly known as the New Communist Party of Australia",
        "I think you are high on the lies told by storm front",
        "You the hell listens to storm front.",
        '" Peter Watson (of Warwick, Qld.) has claimed to represent all sorts of groups, and - in forums - likes to pretend he is several people at the same time',
        "He has a habit of claiming to be the President of organisations he has made up on the internet",
        'He says he is 14 (or 16) years old."',
        "Answere:- No I have not supported lotsd of groups",
        "I have only supported the CPW , AWP (formally known as the NCPA)",
        "I was never a member of the People's Think Tank Association plus the PTTA never had a president",
        "Plus I have only ever been one person",
        "And that person is Peter Watson",
        'So I can only say on thing ""go get a life man"".',
    ]

    chunked_texts = CLASSIFIER.split_text_into_sections(
        """
To implement a simple Moving Average (SMA) crossover strategy for the Apple (AAPL) stock and include risk management and buy/sell quantity, you can use the following code:


```python
import pandas as pd

# Define the technical indicators
fast_length = 20
ema = talib.EMA(fast_length)
data = pd.read_csv('AAPL_data.csv')
fast_ema = ema[data['Close'] < fast_length].index[0]

# Check for crossovers
if fast_ema[0] > slow_ema[0]:
    # Buy
    buy_quantity = int(fast_length * data['Volume'] / 2)
        """,
    )
    assert chunked_texts == [
        "To implement a simple Moving Average (SMA) crossover strategy for the Apple (AAPL) stock and include risk "
        "management and buy/sell quantity, you can use the following code:",
        "```python",
        "import pandas as pd",
        "# Define the technical indicators",
        "fast_length = 20",
        "ema = talib.EMA(fast_length)",
        "data = pd.read_csv('AAPL_data.csv')",
        "fast_ema = ema[data['Close'] < fast_length].index[0]",
        "# Check for crossovers",
        "if fast_ema[0] > slow_ema[0]:",
        "# Buy",
        "buy_quantity = int(fast_length * data['Volume'] / 2)",
    ]

    chunked_texts = CLASSIFIER.split_text_into_sections(
        """
        *This is a test*
        **This is a test**
        """,
    )

    chunked_texts = CLASSIFIER.split_text_into_sections(
        """
        **** Replace this with a single asterisk ****
        Th**s will not be re****placed
        ----- This will be replaced -----
        ===== This will be replaced =====
        """,
    )
    assert chunked_texts == [
        "* Replace this with a single asterisk *",
        "Th**s will not be re****placed",
        "- This will be replaced -",
        "= This will be replaced =",
    ]


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "text, expected_result",
    [
        ("f*ck", [True]),
        ("b!+ch", [True]),
        ("5h!t", [True]),
        ("s#it", [True]),
        ("s#i+", [True]),
        ("s h i t", [False]),
        ("f***ck dendr**hilia", [False]),
        ("f*********ck dendr*****philia", [False]),
        ("f***ck dendr**hilia \n f*********ck dendr*****philia", [False, False]),
        ("f***ck \n dendr**hilia", [False, False]),
    ],
)
def test_profanity_detection_with_character_replacement(
    text: str,
    expected_result: list[bool],
):
    profanity_result = [
        detect_profanity(section)
        for section in CLASSIFIER.split_text_into_sections(text)
    ]
    assert profanity_result == expected_result


@pytest.mark.unit_tests
def test_profanity_regex_against_dictionary():
    for word in ENGLISH_DICTIONARY:
        if word in FULLY_BAD_WORDS:
            assert detect_profanity(word) == True
        else:
            assert detect_profanity(word) == False
