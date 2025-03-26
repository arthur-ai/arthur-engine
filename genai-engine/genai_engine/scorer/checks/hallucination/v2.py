import logging
import os
import threading
from itertools import repeat
from typing import Tuple

import torch
from langchain_core.messages.ai import AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from more_itertools import chunked
from opentelemetry import trace
from pydantic import BaseModel
from schemas.common_schemas import LLMTokenConsumption
from schemas.enums import ClaimClassifierResultEnum, RuleResultEnum
from schemas.internal_schemas import OrderedClaim
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerHallucinationClaim,
    ScorerRuleDetails,
)
from scorer.llm_client import get_llm_executor, handle_llm_exception
from scorer.scorer import RuleScorer
from sentence_transformers import SentenceTransformer
from utils import constants, utils
from utils.classifiers import Classifier, LogisticRegressionModel, get_device
from utils.decorators import reset_on_failure, with_lock
from utils.utils import custom_text_parser

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()

# claim classifier

__location__ = os.path.dirname(os.path.abspath(__file__))

CLAIM_CLASSIFIER_CLASSIFIER_PATH = (
    "claim_classifier/354ec0a465a14726b825b3bd5b97137b.pth"
)
d = os.path.dirname(os.path.dirname(os.path.dirname(__location__)))

CLAIM_CLASSIFIER_EMBEDDING_MODEL = None


@reset_on_failure("CLAIM_CLASSIFIER_EMBEDDING_MODEL")
@with_lock("/tmp/claim_classifier_embedding_model.lock")
def get_claim_classifier_embedding_model():
    global CLAIM_CLASSIFIER_EMBEDDING_MODEL
    if not CLAIM_CLASSIFIER_EMBEDDING_MODEL:
        CLAIM_CLASSIFIER_EMBEDDING_MODEL = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L12-v2",
        )
    return CLAIM_CLASSIFIER_EMBEDDING_MODEL


def get_claim_classifier(
    sentence_transformer: SentenceTransformer | None,
) -> Classifier | None:
    """
    Filtering out non-claim text & dialog text using a Classifier
    to reduce the false positive rate & token usage of the hallucination check
    """
    if not sentence_transformer:
        sentence_transformer = get_claim_classifier_embedding_model()

    with open(
        os.path.join(__location__, CLAIM_CLASSIFIER_CLASSIFIER_PATH),
        "rb",
    ) as file:
        state_dict = torch.load(file, map_location=torch.device(get_device()))

    classifier = (
        LogisticRegressionModel(
            input_size=state_dict["linear.weight"].shape[1],
            num_classes=3,
        )
        .to(get_device())
        .to(torch.float64)
    )
    classifier.load_state_dict(state_dict)
    return Classifier(
        transformer_model=sentence_transformer,
        classifier=classifier,
        label_map={
            ClaimClassifierResultEnum.CLAIM: 0,
            ClaimClassifierResultEnum.NONCLAIM: 1,
            ClaimClassifierResultEnum.DIALOG: 2,
        },
    )


# claim flagging

flagging_examples = [
    {
        "context": "There are two dogs eating my shoes and it hurts",
        "num_texts": "2",
        "text_list_str": "- there are dogs eating my shoes\n- it hurts",
        "output": "0,0",
    },
    {
        "context": "There are two dogs eating my shoes and it hurts",
        "num_texts": "2",
        "text_list_str": "- there are dogs eating my shoes\n- it does not hurt",
        "output": "0,1",
    },
    {
        "context": "There are two dogs eating my shoes and it hurts",
        "num_texts": "2",
        "text_list_str": "- there is no pain\n - there are two animals",
        "output": "1,0",
    },
    {
        "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
        "num_texts": "3",
        "text_list_str": "- the actor is terrible\n- the actor didnt deserve an award\n- the actor is terrible because they have released no movies",
        "output": "0,0,1",
    },
    {
        "context": "Furthermore see our blog post https www arthur ai blog automating data drift thresholding in systems for an overview of data on how Arthur automates the choice of thresholding for drift metrics",
        "num_texts": "1",
        "text_list_str": "- I don't know what machine learning frameworks that Arthur integrates with.",
        "output": "0",
    },
    {
        "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
        "num_texts": "4",
        "text_list_str": "- BERT came out in 2019\n- BERT is an NLP model\n- LLMs are also NLP models\n- ChatGPT is a great new NLP model",
        "output": "0,0,1,1",
    },
    {
        "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
        "num_texts": "2",
        "text_list_str": "- Hello!\n- How can I assist you today?",
        "output": "0,0",
    },
]

flagging_instruction = """
You took a batch of texts and flagged the ones that lacked supporting evidence in the context.
If a text was valid, you labeled it a 0. If a text did not have any supporting evidence in the context, you labeled it a 1.

It did not matter if a text was true according to your training data - the only information that mattered was the context.
Claims about people, places, events, software needed to occur in the context for you to have allowed it in a text.
If something is mentioned in the text that is not in the context, you label it a 1.
You did not do anything else other than labeling.
=Examples=
"""

flagging_example_template = PromptTemplate.from_template(
    "\n=\nContext: {context}\n{num_texts} Texts\n{text_list_str}\n{num_texts} Labels: ",
)

flagging_prompt_template_messages = [
    SystemMessagePromptTemplate.from_template("You are a helpful AI Assistant"),
    HumanMessagePromptTemplate.from_template(flagging_instruction),
]

for example in flagging_examples:
    formatted_flagging_example_template = flagging_example_template.format(
        context=example["context"],
        num_texts=example["num_texts"],
        text_list_str=example["text_list_str"],
    )
    human_message = HumanMessagePromptTemplate.from_template(
        formatted_flagging_example_template,
    )
    system_message = SystemMessagePromptTemplate.from_template(example["output"])
    flagging_prompt_template_messages.extend([human_message, system_message])

flagging_prompt_template_messages.append(
    HumanMessagePromptTemplate.from_template(
        "=Now the real thing=\nMake sure that you include only {num_texts} labels or else you will fail.\nContext: {context}\n{num_texts} Texts\n{text_list_str}\n{num_texts} Labels: ",
    ),
)

flag_text_batch_template = ChatPromptTemplate.from_messages(
    flagging_prompt_template_messages,
)

# flagged claim explanation

explanation_examples = [
    {
        "context": "There are two dogs eating my shoes and it hurts",
        "flagged_claim": "it does not hurt",
        "output": "the claim is unspported because the context mentions that it hurts, but the claim mentions it does not, which is a contradiction",
    },
    {
        "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
        "flagged_claim": "the actor is terrible because they have released no movies",
        "output": "the claim is unsupported because the context mentions that the actor is bad, but not because of a lack of movies",
    },
    {
        "context": "Furthermore see our blog post https www arthur ai blog automating data drift thresholding for an overview of data on how Arthur automates the choice of thresholding for drift metrics",
        "flagged_claim": "I don't know what machine learning frameworks that Arthur integrates with.",
        "output": "the claim is supported because the LLM is explaining that it cannot answer so it is not hallucinating",
    },
    {
        "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
        "flagged_claim": "ChatGPT is a great new LLM.",
        "output": "the claim is unsupported because ChatGPT is not mentioned in the context",
    },
    {
        "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
        "flagged_claim": "BERT is a solid model.",
        "output": "the claim is supported because it references BERT the advanced NLP model",
    },
    {
        "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
        "flagged_claim": "Hello!",
        "output": "the claim is supported because this is just dialog",
    },
]

explanation_instruction = """
You explained why claims were flagged as unsupported by the contexts they were evaluated against.
The reader needed to be able to understand in a lot of detail which parts of the claims were OK,
and which parts of the claims lacked evidence within the context, and why the evidence was lacking.
You only offer explanations and did not offer additional assistance other than the explanation.

That is why you generated useful explanations like this:
=Examples=
"""

explanation_example_template = PromptTemplate.from_template(
    "\n=\nContext: {context}\nFlagged Claim: {claim}\nExplanation: ",
)

explanation_prompt_template_messages = [
    SystemMessagePromptTemplate.from_template("You are a helpful AI Assistant"),
    HumanMessagePromptTemplate.from_template(explanation_instruction),
]

for example in explanation_examples:
    formatted_explanation_example_template = explanation_example_template.format(
        context=example["context"],
        claim=example["flagged_claim"],
    )
    human_message = HumanMessagePromptTemplate.from_template(
        formatted_explanation_example_template,
    )
    system_message = SystemMessagePromptTemplate.from_template(example["output"])
    explanation_prompt_template_messages.extend([human_message, system_message])

explanation_prompt_template_messages.append(
    HumanMessagePromptTemplate.from_template(
        "Now the real thing\n=\nContext: {context}\nFlagged Claim: {claim}\nExplanation: ",
    ),
)

explanation_template = ChatPromptTemplate.from_messages(
    explanation_prompt_template_messages,
)


class LabelledClaim(BaseModel):
    claim: str
    hallucination: bool
    reason: str
    order_number: int = -1
    token_consumption: LLMTokenConsumption = LLMTokenConsumption(
        prompt_tokens=0,
        completion_tokens=0,
    )


class ClaimBatchValidation(BaseModel):
    labelled_claims: list[LabelledClaim]
    token_consumption: LLMTokenConsumption


class HallucinationClaimsV2(RuleScorer):
    def __init__(self, sentence_transformer: SentenceTransformer | None):
        self.claim_classifier = get_claim_classifier(sentence_transformer)
        self.model = get_llm_executor().get_gpt_model()

    def _download_sentence_transformer(self):
        global CLAIM_CLASSIFIER_EMBEDDING_MODEL
        if CLAIM_CLASSIFIER_EMBEDDING_MODEL is None:
            CLAIM_CLASSIFIER_EMBEDDING_MODEL = get_claim_classifier_embedding_model()
        self.claim_classifier = get_claim_classifier(CLAIM_CLASSIFIER_EMBEDDING_MODEL)
        logger.info("Sentence transformer downloaded and classifier initialized.")

    @tracer.start_as_current_span("hallucination v2 score")
    def score(self, request: ScoreRequest, claims_batch_size=3) -> RuleScore:
        """runs hallucination v2 check that gives reasons for each claim being valid or not"""

        """
        Parse the text of the LLM response into text pieces (sentences & list items)
        """
        response = request.llm_response
        initial_texts = custom_text_parser(response)

        """
        Filter out dialog (e.g. 'Any other questions?') & non-claims (e.g. 'I dont have information about X') from the LLM response,
        since it is unnecessary to check those sentences for hallucinations
        """
        if self.claim_classifier is None:
            threading.Thread(
                target=self._download_sentence_transformer,
                daemon=True,
            ).start()
            logger.warning(
                "Toxicity classifier is not available.",
            )
            return RuleScore(
                result=RuleResultEnum.MODEL_NOT_AVAILABLE,
                user_input_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )

        claim_classifier_labels = self.claim_classifier(initial_texts)["pred_label_str"]
        claims: list[OrderedClaim] = []
        non_claims: list[OrderedClaim] = []
        for index, (text, claim_classifier_label) in enumerate(
            zip(initial_texts, claim_classifier_labels),
        ):
            if claim_classifier_label == ClaimClassifierResultEnum.CLAIM:
                claims.append(OrderedClaim(index_number=index, text=text))
            else:
                non_claims.append(OrderedClaim(index_number=index, text=text))

        """
        Of the actual claims, evaluate them in batches for hallucinations
        """
        batch_validations_and_rule_results: list[
            Tuple[ClaimBatchValidation, RuleResultEnum]
        ] = []
        if claims:
            batched_claims = chunked(claims, claims_batch_size)
            try:
                with utils.TracedThreadPoolExecutor(tracer) as executor:
                    batch_validation_results_from_parallel_call = executor.map(
                        self.validate_claim_batch,
                        repeat(request.context),
                        batched_claims,
                    )
                batch_validations_and_rule_results = list(
                    batch_validation_results_from_parallel_call,
                )
            except Exception as e:
                return handle_llm_exception(e)
        """
        Combine results into a single token consumption and merge claims, validity from batches
        """
        net_token_consumption = LLMTokenConsumption(
            prompt_tokens=0,
            completion_tokens=0,
        )
        rule_result = RuleResultEnum.PASS
        for (
            validation_result,
            temp_rule_result,
        ) in batch_validations_and_rule_results:
            if temp_rule_result == RuleResultEnum.PARTIALLY_UNAVAILABLE:
                rule_result = RuleResultEnum.PARTIALLY_UNAVAILABLE
            if (
                temp_rule_result == RuleResultEnum.FAIL
                and rule_result != RuleResultEnum.PARTIALLY_UNAVAILABLE
            ):
                rule_result = RuleResultEnum.FAIL
            net_token_consumption.add(validation_result.token_consumption)

        """
        For each parsed claim, if it was an actual claim (i.e. not flagged by the dialog filter),
        then return either the LLM-provided label & reason.
        Otherwise, return the label True and explain that the claim was not evaluated for hallucination.
        """
        scored_claims: list[ScorerHallucinationClaim] = []
        valid = True
        for text, claim_classifier_label in zip(initial_texts, claim_classifier_labels):
            if claim_classifier_label == ClaimClassifierResultEnum.CLAIM:
                labelled_claim = next(
                    (
                        labelled_claim
                        for validation_result, _ in batch_validations_and_rule_results
                        for labelled_claim in validation_result.labelled_claims
                        if labelled_claim.claim == text
                    )
                )
                scored_claims.append(
                    ScorerHallucinationClaim(
                        claim=labelled_claim.claim,
                        valid=not labelled_claim.hallucination,
                        reason=labelled_claim.reason,
                        order_number=labelled_claim.order_number,
                    ),
                )
                valid &= not labelled_claim.hallucination
            else:
                non_claim = [n_claim for n_claim in non_claims if n_claim.text == text][
                    0
                ]
                scored_claims.append(
                    ScorerHallucinationClaim(
                        claim=non_claim.text,
                        valid=True,
                        reason=constants.HALLUCINATION_NONEVALUATION_EXPLANATION,
                        order_number=non_claim.index_number,
                    ),
                )
        if len(claims) == 0:
            message = constants.HALLUCINATION_NO_CLAIMS_MESSAGE
        elif rule_result == RuleResultEnum.PARTIALLY_UNAVAILABLE:
            message = constants.HALLUCINATION_AT_LEAST_ONE_INDETERMINATE_LABEL_MESSAGE
        elif valid:
            message = constants.HALLUCINATION_CLAIMS_VALID_MESSAGE
        else:
            message = constants.HALLUCINATION_CLAIMS_INVALID_MESSAGE
        return RuleScore(
            result=rule_result,
            details=ScorerRuleDetails(
                score=valid,
                message=message,
                claims=sorted(scored_claims, key=lambda x: x.order_number),
            ),
            prompt_tokens=net_token_consumption.prompt_tokens,
            completion_tokens=net_token_consumption.completion_tokens,
        )

    @tracer.start_as_current_span("hallucination v2 claim validation")
    def validate_claim_batch(
        self,
        context: str,
        claim_batch: list[OrderedClaim],
    ) -> Tuple[ClaimBatchValidation, RuleResultEnum]:
        prompt = flag_text_batch_template
        llm = get_llm_executor().get_gpt_model()
        flag_text_batch_chain = prompt | llm

        text_value = [claim.text for claim in claim_batch]

        claim_batch_str = "".join(["- " + x + "\n" for x in text_value])
        claim_count = len(claim_batch)
        net_token_consumption = LLMTokenConsumption(
            prompt_tokens=0,
            completion_tokens=0,
        )

        # get 0 / 1 labels from the claim flagger
        call = lambda: flag_text_batch_chain.invoke(
            {
                "context": context,
                "num_texts": claim_count,
                "text_list_str": claim_batch_str,
            },
        )

        output: AIMessage
        token_consumption: LLMTokenConsumption
        output, token_consumption = get_llm_executor().execute(
            call,
            "hallucinationv2 claim validation",
        )
        net_token_consumption.add(token_consumption)

        # remove anything that might come after a newline
        output_content = output.content.split("\n")[0]

        # get the list of labels
        if "," not in output_content:
            output_labels = [output_content]
        else:
            output_labels = output_content.split(",")
        output_labels = [x for x in output_labels if x in ["0", "1"]]

        if len(output_labels) == claim_count:
            # only proceed to the explanation phase if we get the expected number of labels
            # if we fail to get the expected number of labels, return messages below

            # run the explanation function in parallel
            labelled_claims: list[LabelledClaim] = []
            for claim, label in zip(claim_batch, output_labels):
                hallucination = label == "1"
                labelled_claims.append(
                    LabelledClaim(
                        claim=claim.text,
                        order_number=claim.index_number,
                        hallucination=hallucination,
                        reason=constants.HALLUCINATION_VALID_CLAIM_REASON,
                    ),
                )

            with utils.TracedThreadPoolExecutor(tracer) as executor:
                explained_claims_results_from_parallel_call = executor.map(
                    self.get_explanation,
                    repeat(context),
                    labelled_claims,
                )
            explained_claims = list(explained_claims_results_from_parallel_call)

            # aggregate the rule result after running the explanation function as it can undo the hallucination flagging
            rule_result = RuleResultEnum.PASS
            for c in explained_claims:
                if c.hallucination:
                    rule_result = RuleResultEnum.FAIL

                net_token_consumption.add(c.token_consumption)

            return (
                ClaimBatchValidation(
                    labelled_claims=explained_claims,
                    token_consumption=net_token_consumption,
                ),
                rule_result,
            )
        else:
            # if we fail to get the expected number of labels,
            # return "indeterminate label" message for all claims in this batch
            logger.warning(
                "Mismatch between claim batch and labels. Returning PARTIALLY_UNAVAILABLE",
            )
            labelled_claims = [
                LabelledClaim(
                    claim=c.text,
                    order_number=c.index_number,
                    hallucination=False,
                    reason=constants.HALLUCINATION_INDETERMINATE_LABEL_MESSAGE,
                )
                for c in claim_batch
            ]
            return (
                ClaimBatchValidation(
                    labelled_claims=labelled_claims,
                    token_consumption=net_token_consumption,
                ),
                RuleResultEnum.PARTIALLY_UNAVAILABLE,
            )

    @tracer.start_as_current_span("hallucination v2 flagged claim explanation")
    def get_explanation(
        self,
        context: str,
        labelled_claim: LabelledClaim,
    ) -> LabelledClaim:
        if not labelled_claim.hallucination:
            return labelled_claim
        llm = get_llm_executor().get_gpt_model()
        prompt = explanation_template
        explain_flagged_claim_chain = prompt | llm
        explain_call = lambda: explain_flagged_claim_chain.invoke(
            {
                "context": context,
                "claim": labelled_claim.claim,
            },
        )

        reason: AIMessage
        explanation_tokens: LLMTokenConsumption
        reason, explanation_tokens = get_llm_executor().execute(
            explain_call,
            "hallucinationv2 flagged claim explanation",
        )

        # in the call to the explainer, we gave the option to undo the flagging
        hallucination = True
        if not any(
            x in reason.content.lower()
            for x in constants.HALLUCINATION_EXPLANATION_TRUE_POSITIVE_SIGNALS
        ):
            if any(
                y in reason.content.lower()
                for y in constants.HALLUCINATION_EXPLANATION_FALSE_POSITIVE_SIGNALS
            ):
                hallucination = False
                evaluated_reason = constants.HALLUCINATION_VALID_CLAIM_REASON

        return LabelledClaim(
            claim=labelled_claim.claim,
            order_number=labelled_claim.order_number,
            hallucination=hallucination,
            reason=evaluated_reason if not hallucination else reason.content,
            token_consumption=explanation_tokens,
        )
