import random

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleScope, RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_create_prompt(client: GenaiEngineTestClientBase):
    status_code, prompt_result = client.create_prompt("cool prompt for this test")
    assert status_code == 200

    return prompt_result


@pytest.mark.unit_tests
def test_create_prompt_with_user_id(client: GenaiEngineTestClientBase):
    status_code, prompt_result = client.create_prompt(
        "cool prompt for this test",
        user_id="testUser",
    )
    assert status_code == 200

    assert prompt_result.user_id == "testUser"

    return prompt_result


@pytest.mark.unit_tests
def test_create_response(client: GenaiEngineTestClientBase):
    prompt_result = test_create_prompt(client)
    status_code, response_result = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
    )
    assert status_code == 200

    return response_result


@pytest.mark.unit_tests
def test_create_response_fails_duplicates(client: GenaiEngineTestClientBase):
    prompt_result = test_create_prompt(client)
    status_code, response_result = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
    )
    assert status_code == 200

    status_code, response_result = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_user_story_create_task_send_prompt_response(client: GenaiEngineTestClientBase):
    status_code, task_response = client.create_task("test_task")
    assert status_code == 200

    status_code, prompt_result = client.create_prompt(
        "cool prompt for this test",
        task_id=task_response.id,
    )
    assert status_code == 200

    status_code, response_result = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
        task_id=task_response.id,
    )
    assert status_code == 200


@pytest.mark.unit_tests
def test_user_story_create_prompt_send_feedback(client: GenaiEngineTestClientBase):
    status_code, task_response = client.create_task("test_task")
    assert status_code == 200

    status_code, prompt_result = client.create_prompt(
        "cool prompt for this test",
        task_id=task_response.id,
    )
    assert status_code == 200

    inference_id = prompt_result.inference_id
    reason = "this was bad"
    feedback_sc = client.send_chat_feedback(inference_id, "prompt_results", 1, reason)
    assert feedback_sc == 201

    status_code, query_resp = client.query_inferences(
        sort="desc",
        page_size=1,
        task_ids=[task_response.id],
    )
    inferences = query_resp.inferences

    target_inference = [i for i in inferences if i.id == inference_id]
    target_inference_feedback = target_inference[0].inference_feedback[0]

    assert target_inference_feedback is not None
    assert target_inference_feedback.score == 1
    assert target_inference_feedback.reason == reason


@pytest.mark.unit_tests
def test_user_story_create_task_send_prompt_with_conversation_id(
    client: GenaiEngineTestClientBase,
):
    status_code, task_response = client.create_task("test_task32")
    assert status_code == 200

    status_code, prompt_result = client.create_prompt(
        "cool prompt for this test",
        task_id=task_response.id,
        conversation_id="conversationid123",
    )
    assert status_code == 200


@pytest.mark.unit_tests
def test_user_story_create_task_create_custom_scoped_rule_send_prompt_response(
    client: GenaiEngineTestClientBase,
):
    status_code, task_response = client.create_task("test_task")
    assert status_code == 200

    custom_keyword = str(random.random())
    rule_name = str(random.random())
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.KEYWORD,
        keywords=[custom_keyword],
    )
    assert status_code == 200
    assert rule.scope == RuleScope.DEFAULT

    status_code, prompt_result = client.create_prompt(
        "cool prompt for this test",
        task_id=task_response.id,
    )

    assert status_code == 200
    for rule_result in prompt_result.rule_results:
        if rule_result.name == rule_name:
            return
    # Our custom rule scoped to this task was not run.
    assert False


@pytest.mark.unit_tests
def test_user_story_create_task_validate_large_prompt_no_error(
    client: GenaiEngineTestClientBase,
):
    # create a new task
    status_code, task_response = client.create_task(
        "test_user_story_create_task_validate_large_prompt_no_error",
    )
    assert status_code == 200

    # delete the default rules on the newly created task
    for rule in task_response.rules:
        client.delete_task_rule(task_id=task_response.id, rule_id=rule.id)

    # prompt injection
    rule_name = str(random.random())
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.PROMPT_INJECTION,
        task_id=task_response.id,
    )
    assert status_code == 200
    assert rule.scope == RuleScope.TASK

    # pii
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.PII_DATA,
        task_id=task_response.id,
    )
    assert status_code == 200
    assert rule.scope == RuleScope.TASK

    # keyword
    custom_keyword = str(random.random())
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.KEYWORD,
        keywords=[custom_keyword],
        task_id=task_response.id,
    )
    assert status_code == 200
    assert rule.scope == RuleScope.TASK

    # toxicity - commented out for now as this rule takes too long to process this prompt and times out on ALB
    # status_code, rule = client.create_rule(
    #     rule_name, rule_type=RuleType.TOXICITY, task_id=task_response.id
    # )
    # assert status_code == 200
    # assert rule.scope == RuleScope.TASK

    # sensitive data
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.MODEL_SENSITIVE_DATA,
        task_id=task_response.id,
    )
    assert status_code == 200
    assert rule.scope == RuleScope.TASK

    # regex
    status_code, rule = client.create_rule(
        rule_name,
        rule_type=RuleType.REGEX,
        task_id=task_response.id,
    )
    assert status_code == 200
    assert rule.scope == RuleScope.TASK

    # run prompt validation
    status_code, prompt_result = client.create_prompt(
        "The Black Mountain School    What came to be known as the Black Mountain School of poetry "
        "represented, in mid twentieth-century America, the crossroads of poetic innovation. The name of this poetic "
        "movement derives from Black Mountain College in North Carolina, an experimental college founded in 1933. By "
        "the time the poet and essayist Charles OLSON became its Rector in 1950, it had become a mecca for a larger "
        "artistic and intellectual avant-garde. Until it closed in 1957, the college was the seedbed for virtually all "
        "of America’s later artistic innovations. A vast array of writers, painters, sculptors, dancers, composers and "
        "many other people involved in the creative arts passed through the college’s doors as teachers or "
        "students.\n\nThe poets most often associated with the name Black Mountain are, primarily, Olson, Robert "
        "CREELEY and Robert DUNCAN, along with Denise LEVERTOV, Paul BLACKBURN, Paul Carroll, William BRONK, Larry "
        "EIGNER, Edward DORN, Jonathan Williams, Joel OPPENHEIMER, John WIENERS, Theodore ENSLIN, Ebbe Borregard, "
        "Russell EDSON, M.C. Richards, and Michael Rumaker (a few of whom never attended the college but are "
        "associated with the college group because of their poetic styles or their representation in certain "
        "literary magazines discussed below). Many other important intellectuals and artists were also involved in "
        "what amounted to an artistic revolution.\n\nToday, Black Mountain poetry may seem to contain a great variety "
        "of styles and themes. Regardless, there are some common characteristics to be noticed in this poetry: the "
        "use of precise language, direct statement, often plain (even blunt) diction, and metonymy rather than "
        "metaphor or simile. These writerly tendencies evolved in reaction to earlier poetry that was strictly "
        "metered, end-rhymed, filled with aureate diction and monumental subject matter. The reaction by the "
        "Black Mountain poets was a continuation of a poetic revolution begun by the IMAGISTS and later the "
        "OBJECTIVISTS. In general, Black Mountain poets typically refrain from commenting on their personal "
        "appraisal of a scene evoked in a poem, and this strategy can even mean the avoidance of adjectives and "
        "adverbs. As Ezra Pound had pronounced early in the century (in describing the poetry of H.D.), poetry "
        'should be "laconic speech," "Objective," without "slither—direct," and containing "No metaphors '
        "that won't permit examination.-- It's straight talk.\" Besides its alignment with Imagism and later "
        "Objectivism, Black Mountain poetry can be said to descend, especially in its embrace of individualism, "
        "from such nineteenth-century New England writers as Henry David Thoreau and particularly Ralph Waldo Emerson. "
        'As Edward Foster has written, Emerson’s essay "Self-Reliance" gave the many Black Mountain poets, "despite '
        "their radical differences in personality, sensibility, and general ambitions, a common apprehension about "
        'what a poem might achieve" (xiii). The poem could be an extension of themselves as persons, as individuals '
        "standing apart from the ideals of an orthodox past.\n\nPhilosophically, Black Mountain poetry also shares "
        "a view of reality—of the physical world and humanity’s relationship to it—derived from scientific movements "
        "of its time, movements that contradicted the view of a stable and predictable universe set forth by Sir Isaac "
        "Newton and later Immanuel Kant. Olson, Creeley, Duncan and others were interested in the ideas of Albert "
        "Einstein, who formulated the theory of relativity, and Werner Heisenberg who postulated his theory of "
        "uncertainty relations, especially. Physical reality was relative to time, according to Einstein; according "
        "to Heisenberg, it was simply indeterminate and incomplete. Therefore, Creeley has argued,\n\nThe world "
        'cannot be "known" entirely. . . . In all disciplines of human attention and act, the possibilities '
        "inherent in the previous conception of a Newtonian universe—with its containment and thus the possibility "
        "of being known—have been yielded. We do not know the world in that way, nor will we. Reality is continuous, "
        "not separable, and cannot be objectified. We cannot stand aside to see it.\nThe reliance in Black Mountain "
        'poetry, and its "objectivist" forebears, on direct statement and metonymy is a symptom of this basic '
        "outlook on the world.: What is unknowable finally can nevertheless be beautiful. This poetry, then, poses "
        'a fundamental problem of perception. In "Love," an early poem by Creeley, there are the sure '
        '"particulars" such as "oak, the grain of, oak," and there are also, by contrast, "what supple shadows '
        'may come / to be here." These details hold within themselves a tension between the stable and the radical, '
        "the known and the continually evolving.\nThe literary magazines associated with the Black Mountain school, "
        "The Black Mountain Review, Origin and, to a lesser extent the San Francisco Review, were a haven for writers "
        "whose aesthetics and point of view were found to be unacceptable by the mainstream journals of the time. "
        "Indeed, it is within the issue of these magazines that the Black Mountain sensibility truly coalesces. "
        "Edited by Creeley and Cid CORMAN, respectively, the The Black Mountain Review and Origin published now well "
        "known figures such as (besides the poets named above) Jorge Luis Borges, William Burroughs "
        "(under the name of William Lee), Paul Celan, Judson Crews, René Daumal, Fielding Dawson, André du Bouchet, "
        "Katue Kitasono, Irving Layton, James MERRILL, Eugenio Montale, Samuel French Morse, James PURDY, Kenneth "
        "REXROTH, Hubert Selby Jr., Kusano Shimpei, Gary SNYDER, John TAGGART, Gael Turnbull, César Vallejo, "
        "Philip WHALEN, Richard WILBUR, and WILLIAM CARLOS WILLIAMS. Later issues of Origin, in the 1960s, featured "
        "work by Louis ZUKOFSKY, Snyder, Zeami Motokiyo, Margaret Avison, Robert KELLY, Ian Hamilton Finlay, Turnbull, "
        "Corman, Duncan, Francis Ponge, Frank Samperi, Lorine NIEDECKER, André du Bouchet, Shimpei, Bronk, Albers "
        "and others.\n\nThe ars poetica of the Black Mountain movement is usually identified with Olson’s 1950 essay "
        '"Projective Verse," published in Poetry New York, a magazine that preceded these others—Olson’s fully '
        "defined formula for poetry being projective or open field verse. In this essay, Olson discusses the "
        "importance of composing poetry according the breath of the individual poet or speaker of a poem and not "
        "according to a predetermined set form of speech or verse. There are two aspects of a poem, he "
        "maintains:\n\nthe HEAD, by way of the EAR, to the SYLLABLE\nthe HEART, by way of the BREATH, to the "
        'LINE[.]\n\nThe breath of the poet "allows all the speech-force of language […]." Moreover, a poem should '
        'never have any slack or, as Olson puts it, "ONE PERCEPTION MUST IMMEDIATELY AND DIRECTLY LEAD TO A '
        'FURTHER PERCEPTION." Hence, the poet must "USE USE USE the process at all points" so that a perception '
        'can "MOVE, INSTANTER, ON ANOTHER." Perhaps the essence of what Olson is trying to say comes from Creeley’s '
        'belief, as quoted by Olson in this essay, that "FORM IS NEVER MORE THAN AN EXTENSION OF CONTENT."\nThe '
        'openness of the poetry Olson advocated can be seen in Duncan’s poem, "Often I Am Permitted to Return to a '
        'Meadow," which begins his volume of poetry entitled, fittingly, The Opening of the Field. In this poem '
        "Duncan is involved with the personal creative process and the bid for freedom that poetry (and implicitly "
        'Black Mountain poetry) makes possible; writing is a "place of first permission," Duncan asserts. The meadow '
        'referred to in the poem’s title is possibly real, tangible, yet it exists, more importantly, "as if it were '
        'a scene made-up by the mind"; still, it is a place apart from the poem’s persona and in fact it is "a made '
        'place, created by light / wherefrom the shadows that are forms fall." Duncan’s vision of poetic reality is '
        "akin, it seems, to a classically Platonic view of the world in which ideal forms reside beyond human "
        "perception, with the things humanity can know similar to them but not perfectly the same, much as shadows of "
        'objects are like the objects themselves. The point here is that we suppose places we inhabit "as if […] '
        'certain bounds [could] hold against chaos" (emphasis added), and therefore the poem stresses how very '
        "delicate perception is, and underscores the individual’s seeing.\n\nLikewise, Olson creates, in his epic "
        "work The Maximus Poems, a towering epic persona, Maximus, who looks out upon a vast geography informed by a "
        "historical past. The singularity of this figure is meant to compare with the immensity of Olson’s subject, "
        "the terrain beneath Maximus’ feet grounded in Gloucester, Massachusetts, and the history beginning in ancient "
        "Greece and running up through a present American time. There is tangibility, as when Maximus says that "
        'there are "facts, to be dealt with"; on the other hand, he asks, "that which matters, that which insists, '
        'that which will last, / that! o my people, where shall you find it, how, where"? In Olson’s work readers '
        "discover an astonishing sweep of history, a breadth of vision, and the eternal verities laid out before "
        "us—yet these truths are tried by Olson, tested, and finally undone. Olson is reconceiving both space "
        "(physical geography) and time (the history of his civilization) according the new paradigms set forth by "
        "Emerson and Thoreau, Einstein and Heisenberg. Yet this grasp doesn’t neglect the eternally human condition, "
        'and accounts for death and suffering as well as triumph and splendor. Hence, in "The Kingfishers," he '
        'observes that human beings are capable of precision: "The factors are / in the animal and/or the machine '
        '[…]"; they "involve [….] a discrete or continuous sequence of measurable events distributed in time […]." '
        "All the same, Olson says that what endures is change itself, a theme he strikes at the poem’s outset and "
        'reprises throughout. "What does not change / is the will to change." This concept is perceivable in all '
        'things: "hear, where the dry blood talks / where the old appetite walks […]."\n\nOlson’s point of view is '
        'echoed in Levertov’s work. In her poem "Beyond the End" human destiny is constrained by natural forces, '
        'yet the point of it all is not merely to "’go on living’ but to quicken, to activate, extend." '
        'The "will to respond" is a force unbounded by reason, and so we reside always "further, beyond the '
        'end / beyond whatever ends: to begin, to be, to defy." What stands out in both Levertov and Olson is the '
        "precise stipulation of limits and the recognition of something outside them, which can best be evoked with "
        "exacting language. This use of language is nicely exemplified by Joel Oppenheimer, who was a student of "
        "Olson, Creeley and others at Black Mountain College. Not only is his work precise, coming out of his student "
        "experience; it is also rhythmic according to the measure of a reader’s breathing, as was stipulated in "
        "Olson’s essay. Moreover, Oppenheimer’s signature diction is for its time breathtakingly casual and candid, "
        "reflecting the social revolution in America that was to reach crisis proportions in the late 1960s. "
        'Oppenheimer’s poetry is located in the moments of a daily life. In his poem "The Bath," the acts of '
        "living, so to speak, are simple, for instance the act of taking a bath. His lover’s bathing, Oppenheimer "
        'finds, is a ritual albeit one unremarked upon but for his verse—and yet, he humorously points out, "she '
        'wants him" (the poem\'s persona thinks) "unbathed"; he is gratified by her desire. The routine of life is '
        'celebrated in the poem by this nexus between the two of them; there is "her continuous bathing. / in his '
        'tub. in his water. wife."\n\nBlack Mountain College was the soil for virtually all later experimental '
        "poetry in America and much of America’s later-century art and music. Grounded in the poetry of Pound and "
        'Williams—as Creeley writes in his homage to Williams, "For W.C.W.," "and and becomes // just so"—as '
        "well as demonstrating great sympathy for the Objectivist poetry of Louis Zukofsky and the others of this "
        "school, the later Black Mountain writers continued a tradition of exact perception and an avoidance of "
        "metaphor, and of a celebration of the individual that would also emerge in BEAT poetry. The Black Mountain "
        "contribution to American poetry and poetics was not merely a new version of these other movements, but rather "
        "was original and arguably the pivotal moment in modern American poetic history.",
        task_id=task_response.id,
    )

    assert status_code == 200
    for rule_result in prompt_result.rule_results:
        assert rule_result.result not in (
            RuleResultEnum.UNAVAILABLE,
            RuleResultEnum.SKIPPED,
        )


@pytest.mark.unit_tests
def test_validations_dont_fail_on_error(client: GenaiEngineTestClientBase):
    status_code, task_response = client.create_task("test_task")
    assert status_code == 200

    custom_keyword = str(random.random())
    rule_name = str(random.random())
    status_code, _ = client.create_rule(
        rule_name,
        rule_type=RuleType.KEYWORD,
        keywords=[custom_keyword],
    )
    assert status_code == 200

    status_code, prompt_result = client.create_prompt(
        "MockScorerClientException",
        task_id=task_response.id,
    )

    assert status_code == 200
    for rule_result in prompt_result.rule_results:
        assert rule_result.result == "Unavailable"
        assert rule_result.details.message == "This rule could not be evaluated"
