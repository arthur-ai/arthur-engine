import logging
import os
import threading
from itertools import repeat

import torch
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum
from langchain_core.messages.ai import AIMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from more_itertools import chunked
from opentelemetry import trace
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from schemas.enums import ClaimClassifierResultEnum
from schemas.internal_schemas import OrderedClaim
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerHallucinationClaim,
    ScorerRuleDetails,
)
from scorer.checks.hallucination.v2_legacy_prompts import (
    get_claim_flagging_prompt,
    get_flagged_claim_explanation_prompt,
)
from scorer.checks.hallucination.v2_prompts import get_structured_output_prompt
from scorer.llm_client import get_llm_executor, handle_llm_exception
from scorer.scorer import RuleScorer
from utils import constants, utils
from utils.claim_parser import ClaimParser
from utils.classifiers import Classifier, LogisticRegressionModel, get_device
from utils.model_load import get_claim_classifier_embedding_model

tracer = trace.get_tracer(__name__)
logger = logging.getLogger()

# claim classifier

__location__ = os.path.dirname(os.path.abspath(__file__))

CLAIM_CLASSIFIER_EMBEDDING_MODEL: SentenceTransformer | None
CLAIM_CLASSIFIER_CLASSIFIER_PATH = (
    "claim_classifier/354ec0a465a14726b825b3bd5b97137b.pth"
)
d = os.path.dirname(os.path.dirname(os.path.dirname(__location__)))


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
        state_dict = torch.load(
            file,
            map_location=torch.device(get_device()),
            weights_only=False,
        )

    classifier = (
        LogisticRegressionModel(
            input_size=state_dict["linear.weight"].shape[1],
            num_classes=3,
        )
        .to(get_device())
        .to(torch.float64)
    )
    classifier.load_state_dict(state_dict)
    classifier.eval()  # Set classifier to evaluation mode
    if not sentence_transformer:
        logger.error("Sentence transformer is not available.")
        return None
    return Classifier(
        transformer_model=sentence_transformer,
        classifier=classifier,
        label_map={
            ClaimClassifierResultEnum.CLAIM: 0,
            ClaimClassifierResultEnum.NONCLAIM: 1,
            ClaimClassifierResultEnum.DIALOG: 2,
        },
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


########################################################
# Classes used as structured output responses
########################################################
class LLMClaimResult(BaseModel):
    claim_text: str
    is_hallucination: bool
    explanation: str


class ReturnClaimFlags(BaseModel):
    results: list[LLMClaimResult]


########################################################


class HallucinationClaimsV2(RuleScorer):
    model: AzureChatOpenAI | ChatOpenAI

    def __init__(self, sentence_transformer: SentenceTransformer | None) -> None:
        self.claim_classifier = get_claim_classifier(sentence_transformer)
        model = get_llm_executor().get_gpt_model()
        if model is None:
            raise RuntimeError(
                "Failed to initialize LLM model for HallucinationClaimsV2. "
                "Check your LLM configuration.",
            )
        self.model = model
        self.claim_parser = ClaimParser()
        self.flag_text_batch_template = get_claim_flagging_prompt()
        self.explanation_template = get_flagged_claim_explanation_prompt()
        self.structured_output_prompt = get_structured_output_prompt()

    def _download_sentence_transformer(self) -> None:
        global CLAIM_CLASSIFIER_EMBEDDING_MODEL
        if CLAIM_CLASSIFIER_EMBEDDING_MODEL is None:
            CLAIM_CLASSIFIER_EMBEDDING_MODEL = get_claim_classifier_embedding_model()
        self.claim_classifier = get_claim_classifier(CLAIM_CLASSIFIER_EMBEDDING_MODEL)
        logger.info("Sentence transformer downloaded and classifier initialized.")

    @tracer.start_as_current_span("hallucination v2 score")
    def score(self, request: ScoreRequest, claims_batch_size: int = 3) -> RuleScore:
        """runs hallucination v2 check that gives reasons for each claim being valid or not"""

        """
        Parse the text of the LLM response into text pieces (sentences & list items)
        """
        response = request.llm_response
        initial_texts = self.claim_parser.process_and_extract_claims(response)

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
            tuple[ClaimBatchValidation, RuleResultEnum]
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
    ) -> tuple[ClaimBatchValidation, RuleResultEnum]:
        if get_llm_executor().supports_structured_outputs():
            return self.validate_claim_batch_structured_output(context, claim_batch)
        else:
            return self.validate_claim_batch_legacy(context, claim_batch)

    def validate_claim_batch_structured_output(
        self,
        context: str,
        claim_batch: list[OrderedClaim],
    ) -> tuple[ClaimBatchValidation, RuleResultEnum]:
        flag_text_batch_chain = (
            self.structured_output_prompt
            | self.model.with_structured_output(ReturnClaimFlags)
        )

        text_value = [claim.text for claim in claim_batch]

        claim_batch_str = "".join(["- " + x + "\n" for x in text_value])
        claim_count = len(claim_batch)
        net_token_consumption = LLMTokenConsumption(
            prompt_tokens=0,
            completion_tokens=0,
        )

        call = lambda: flag_text_batch_chain.invoke(
            {
                "context": context,
                "num_texts": claim_count,
                "text_list_str": claim_batch_str,
            },
        )

        return_claim_flags: ReturnClaimFlags
        token_consumption: LLMTokenConsumption
        return_claim_flags, token_consumption = get_llm_executor().execute(
            call,
            "hallucinationv2 claim validation",
        )

        results = return_claim_flags.results
        net_token_consumption.add(token_consumption)

        if len(results) == claim_count:
            labelled_claims: list[LabelledClaim] = []
            rule_result = RuleResultEnum.PASS

            for i, llm_claim_result in enumerate(results):
                if llm_claim_result.is_hallucination:
                    rule_result = RuleResultEnum.FAIL

                explanation = (
                    llm_claim_result.explanation
                    if llm_claim_result.is_hallucination
                    else "No hallucination detected!"
                )

                labelled_claims.append(
                    LabelledClaim(
                        claim=claim_batch[i].text,
                        hallucination=llm_claim_result.is_hallucination,
                        reason=explanation,
                        order_number=claim_batch[i].index_number,
                    ),
                )

            return (
                ClaimBatchValidation(
                    labelled_claims=labelled_claims,
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

    def validate_claim_batch_legacy(
        self,
        context: str,
        claim_batch: list[OrderedClaim],
    ) -> tuple[ClaimBatchValidation, RuleResultEnum]:
        flag_text_batch_chain = self.flag_text_batch_template | self.model

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
        if isinstance(output.content, str):
            output_content = output.content.split("\n")[0]
        else:
            output_content = "".join([str(x) for x in output.content]).split("\n")[0]

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
        explain_flagged_claim_chain = self.explanation_template | self.model
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
        if isinstance(reason.content, str):
            reason_content = reason.content
        else:
            reason_content = "".join([str(x) for x in reason.content])
        if not any(
            x in reason_content.lower()
            for x in constants.HALLUCINATION_EXPLANATION_TRUE_POSITIVE_SIGNALS
        ):
            if any(
                y in reason_content.lower()
                for y in constants.HALLUCINATION_EXPLANATION_FALSE_POSITIVE_SIGNALS
            ):
                hallucination = False
                evaluated_reason = constants.HALLUCINATION_VALID_CLAIM_REASON

        return LabelledClaim(
            claim=labelled_claim.claim,
            order_number=labelled_claim.order_number,
            hallucination=hallucination,
            reason=evaluated_reason if not hallucination else reason_content,
            token_consumption=explanation_tokens,
        )
