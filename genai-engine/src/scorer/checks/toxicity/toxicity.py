import logging
import os
import re
import threading
from typing import Any, List

import numpy as np
import torch
from arthur_common.models.enums import RuleResultEnum, ToxicityViolationType
from opentelemetry import trace
from transformers import AutoModelForSequenceClassification
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from scorer.checks.toxicity.toxicity_profanity.profanity import detect_profanity
from scorer.scorer import RuleScorer
from utils import constants
from utils.model_load import (
    get_harmful_request_classifier,
    get_profanity_classifier,
    get_toxicity_classifier,
    get_toxicity_model,
    get_toxicity_tokenizer,
)
from utils.text_chunking import ChunkIterator
from utils.utils import get_env_var, list_indicator_regex, pad_text

logger = logging.getLogger()

__location__ = os.path.dirname(os.path.abspath(__file__))

tracer = trace.get_tracer(__name__)

TOXICITY_TOKENIZER: PreTrainedTokenizerBase | None
TOXICITY_MODEL: AutoModelForSequenceClassification | None

HARMFUL_REQUEST_MAX_CHUNK_SIZE = int(
    get_env_var(
        constants.GENAI_ENGINE_TOXICITY_HARMFUL_REQUESTS_CHUNK_SIZE_ENV_VAR,
        True,
    )
    or 512,
)

TOXICITY_MAX_CHUNK_SIZE = int(
    get_env_var(constants.GENAI_ENGINE_TOXICITY_MAX_CHUNK_SIZE_SIZE_ENV_VAR, True)
    or 32,
)

TOXICITY_MODEL_BATCH_SIZE = int(
    get_env_var(constants.GENAI_ENGINE_TOXICITY_MODEL_BATCH_SIZE_ENV_VAR, True) or 64,
)


def replace_special_chars(match: re.Match[str]) -> str | Any:
    return match.group(1)


class ToxicityScorer(RuleScorer):
    LABEL = "TOXIC"

    def __init__(
        self,
        toxicity_model: AutoModelForSequenceClassification | None,
        toxicity_tokenizer: PreTrainedTokenizerBase | None,
        harmful_request_model: PreTrainedModel | None,
        harmful_request_tokenizer: PreTrainedTokenizerBase | None,
    ) -> None:
        self.model = get_toxicity_classifier(toxicity_model, toxicity_tokenizer)
        self.harmfulrequest_classifier = get_harmful_request_classifier(  # type: ignore[func-returns-value]
            harmful_request_model,
            harmful_request_tokenizer,
        )
        self.toxicity_tokenizer = (
            toxicity_tokenizer if toxicity_tokenizer else get_toxicity_tokenizer()
        )
        self.profanity_classifier = get_profanity_classifier()

    def _download_model_and_tokenizer(self) -> None:
        # Download the model and tokenizer using the provided methods
        global TOXICITY_TOKENIZER
        global TOXICITY_MODEL
        if TOXICITY_TOKENIZER is None:
            get_toxicity_tokenizer()
        if TOXICITY_MODEL is None:
            get_toxicity_model()
        self.model = get_toxicity_classifier(TOXICITY_MODEL, TOXICITY_TOKENIZER)
        logger.info("Model and tokenizer downloaded and classifier initialized.")

    def chunk_text(self, text: str, chunk_size: int) -> list[str]:
        if self.toxicity_tokenizer is None:
            raise ValueError(
                "Toxicity tokenizer is not available.",
            )  # TODO: confirm that if tokenizer is not available we should raise error
        chunk_iterator = ChunkIterator(
            text,
            self.toxicity_tokenizer,
            chunk_size,
        )

        return [chunk for chunk in chunk_iterator]

    def split_text_into_sections(self, text: str) -> list[str]:
        """Splits text into sections to localize where toxic text is identified

        Arguments:
            text: str
        Returns:
            List[str]
        """

        # this function uses the list indicator regex to treat an entire list item as one section
        # therefore, something like
        # "1. do this thing"
        # gets treated as a single section instead of spltting the "1" away from the "do this thing"
        pattern = r"(?:\.|\?)(?=\s+[A-Za-z])"
        special_char_pattern = r"(?<![a-zA-Z])([^\w\s])\1{2,}(?![a-zA-Z])"

        lines = text.split("\n")
        texts = []
        for line in lines:
            line = line.strip()
            line = re.sub(special_char_pattern, replace_special_chars, line)
            if list_indicator_regex.match(line):
                texts.append(line)
            else:
                sections = re.split(pattern, line)
                texts.extend([x.strip() for x in sections if x])
        return texts

    def detect_profanity(self, texts: list[str], threshold: float) -> bool:
        """
        Detects profanity using a regex function and a classifier.
        The regex checks a blacklist of common words and their substitutions.
        If a string doesn't contain any blacklisted words explicitly a classifier is used to detect offensive content.

        Inputs:
            texts (List[str]): List of text chunks to be checked for profanity
            threshold (float): Toxicity threshold for the profanity classifier

        Returns:
            bool: True if profanity is detected, False otherwise.
        """
        if self.profanity_classifier is None:
            raise ValueError(
                "Profanity classifier is not available.",
            )  # TODO: confirm that if classifier is not available we should raise error
        with tracer.start_as_current_span("toxicity: profanity detection"):
            for section in texts:
                # this calls the detect_profanity function found in toxicity_profanity/profanity.py
                if detect_profanity(section):
                    # if we detect profanity we can return early since later we check just if any profanity has been detected
                    return True

            prof_inference_res: list[list[dict[str, str | float]]] = self.profanity_classifier(  # type: ignore[assignment]
                texts,
                batch_size=TOXICITY_MODEL_BATCH_SIZE,
            )

            for dicts_arr in prof_inference_res:
                if any(
                    float(label_dict["score"]) > threshold
                    for label_dict in dicts_arr
                    if str(label_dict["label"]) == "OFFENSIVE"
                ):
                    return True
            return False

    def score_harmful_request(self, texts: List[str]) -> list[float]:
        """Scores using a harmful request classifier

        Arguments:
            texts: List[str]
                parsed sections of text from the original ScoreRequest
        Returns:
            (# texts,) list of harmful request probabilities
        """
        if self.harmfulrequest_classifier is None:
            return [0.0] * len(texts)
        with tracer.start_as_current_span("toxicity: run harmful request classifier"):
            results: list[float] = self.harmfulrequest_classifier(texts)["prob"]
            return results

    def score_toxic_text(self, texts: list[str]) -> list[float]:
        """Scores toxicity using toxicity / hate speech classifier

        The pretrained deberta classifier outputs a label of LABEL_1 to represent the presence of toxicity/hate speech
        Arguments:
            texts: List[str]
                parsed sections of text from the original ScoreRequest
        Returns:
            (# texts,) list of toxicity probabilities
        """
        if self.model is None:
            logger.warning(
                "Toxicity model is not available.",
            )  # TODO: confirm that if model is not available we should return an empty list or raise error
            return []
        with tracer.start_as_current_span("toxicity: run deberta classifier"):
            # note: a flaw in the model was identified Mar 18 2024
            # it was fine-tuned as a classifier on almost 0 examples of text < 20 chars
            # so for now, we apply repetition padding to the input sequences
            with torch.no_grad():
                # why we ignore assignment type error?
                # return type in the transformers library is typed wrongly
                # it returns list nested in list of dicts with label and score keys
                tox_results: list[list[dict[str, str | float]]] = self.model(  # type: ignore[assignment]
                    pad_text(texts, pad_type="repetition"),
                    batch_size=TOXICITY_MODEL_BATCH_SIZE,
                )
        toxscores: list[float] = []
        for l in tox_results:
            for l_ in l:
                if str(l_["label"]).upper() == self.LABEL:
                    toxscores.append(float(l_["score"]))
        return toxscores

    def write_score_details_message(
        self,
        profanity_results: bool,
        harmscores: list[float],
        toxscores: list[float],
        threshold: float,
    ) -> str:
        """
        Aggregates all our rule results & model predictions into a written message for the ScoreDetails

        Arguments:
            texts : List[str]
            profanity_results : List[bool]
            harmscores : List[float]
            toxscores : List[float]
            threshold : float
        Returns:
            message: str
                message to be provided to the user (TBD on specific presentation of details)
        """
        if (
            profanity_results
            or any(np.round(s, 3) > threshold for s in harmscores)
            or any(np.round(s, 3) > threshold for s in toxscores)
        ):
            return "Toxicity detected"
        return "No toxicity detected!"

    def score(self, request: ScoreRequest) -> RuleScore:
        """Generates a toxicity score for a request

        Splits request.scoring_text into sections to identify which section(s), if any, contain toxic text

        Uses multiple classifiers to detect multiple types of toxic text

        Arguments:
            request: ScoreRequest
                scoring_text: str
                    the text to be parsed & assessed for toxicity
                toxicity_threshold: float
                    user-provided value in (0,1), above which a toxicity score yields a genai-engine FAIL
        Returns:
            RuleScore
                result: RuleResultEnum
                    the maximum of the generated toxicity score(s)
                details: ScorerRuleDetails
                    message: str
                        the description of each type of toxicity caught
                    toxicity_score: float
                        the maximum of the generated toxicity score(s)
                all token return values 0
        """
        if self.model is None:
            threading.Thread(
                target=self._download_model_and_tokenizer,
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

        if not isinstance(request.toxicity_threshold, float):
            raise ValueError("Toxicity threshold must be a float")

        if not request.scoring_text:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        text_chunks = self.chunk_text(request.scoring_text, TOXICITY_MAX_CHUNK_SIZE)

        harmful_request_text_chunks = self.chunk_text(
            request.scoring_text,
            HARMFUL_REQUEST_MAX_CHUNK_SIZE,
        )

        # generate rule results & model predictions
        profanity_results = self.detect_profanity(
            text_chunks,
            request.toxicity_threshold,
        )

        harmfulrequest_scores = []
        toxicity_scores = []

        # aggregate rule results & model predictions into the returned RuleScore
        if profanity_results:
            # return 0.9999999999... if profanity
            final_score = np.nextafter(1.0, 0.0)
            final_problem_type = ToxicityViolationType.PROFANITY  # Keep them as str
        else:
            harmfulrequest_scores = self.score_harmful_request(
                harmful_request_text_chunks,
            )

            # run the toxicity model in batches
            toxicity_scores = self.score_toxic_text(text_chunks)

            # if no profanity, return the maximum score on any section from either of our classifiers
            max_harm, max_tox = max(harmfulrequest_scores), max(toxicity_scores)

            final_score = 0.0
            if max_harm > max_tox:
                final_score = max_harm
                final_problem_type = ToxicityViolationType.HARMFUL_REQUEST
            else:
                final_score = max_tox
                final_problem_type = ToxicityViolationType.TOXIC_CONTENT
        bool_result = final_score > request.toxicity_threshold or profanity_results
        genai_engine_results = {False: RuleResultEnum.PASS, True: RuleResultEnum.FAIL}
        genai_engine_result = genai_engine_results[bool_result]
        message = self.write_score_details_message(
            profanity_results,
            harmfulrequest_scores,
            toxicity_scores,
            request.toxicity_threshold,
        )
        return RuleScore(
            result=genai_engine_result,
            details=ScorerRuleDetails(
                message=message,
                toxicity_score=ScorerToxicityScore(
                    toxicity_score=final_score,
                    toxicity_violation_type=(
                        final_problem_type
                        if bool_result
                        else ToxicityViolationType.BENIGN
                    ),
                ),
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
