import logging
import re
import threading
from typing import List

import numpy as np
import torch
from opentelemetry import trace
from schemas.enums import RuleResultEnum, ToxicityViolationType
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from scorer.checks.toxicity.toxicity_profanity.profanity import detect_profanity
from scorer.scorer import RuleScorer
from transformers import pipeline
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase
from utils import utils
from utils.classifiers import get_device
from utils.model_load import get_toxicity_model, get_toxicity_tokenizer
from utils.utils import list_indicator_regex, pad_text

logger = logging.getLogger()
tracer = trace.get_tracer(__name__)


def get_toxicity_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
):
    if not model:
        model = get_toxicity_model()
    if not tokenizer:
        tokenizer = get_toxicity_tokenizer()
    return pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        top_k=99999,
        truncation=True,
        device=torch.device(get_device()),
    )


def get_harmful_request_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
):
    if not model or not tokenizer:
        return None


class ToxicityScorer(RuleScorer):
    LABEL = "TOXIC"

    def __init__(
        self,
        toxicity_model: PreTrainedModel | None,
        toxicity_tokenizer: PreTrainedTokenizerBase | None,
        harmful_request_model: PreTrainedModel | None,
        harmful_request_tokenizer: PreTrainedTokenizerBase | None,
    ):
        self.model = get_toxicity_classifier(toxicity_model, toxicity_tokenizer)
        self.harmfulrequest_classifier = get_harmful_request_classifier(
            harmful_request_model,
            harmful_request_tokenizer,
        )

    def _download_model_and_tokenizer(self):
        # Download the model and tokenizer using the provided methods
        global TOXICITY_TOKENIZER
        global TOXICITY_MODEL
        if TOXICITY_TOKENIZER is None:
            get_toxicity_tokenizer()
        if TOXICITY_MODEL is None:
            get_toxicity_model()
        self.model = get_toxicity_classifier(TOXICITY_MODEL, TOXICITY_TOKENIZER)
        logger.info("Model and tokenizer downloaded and classifier initialized.")

    def split_text_into_sections(self, text: str):
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
        asterisk_pattern = r"\*{2,}"
        updated_text = re.sub(asterisk_pattern, lambda m: "-" * len(m.group()), text)

        lines = updated_text.split("\n")
        texts = []
        for line in lines:
            line = line.strip()
            if list_indicator_regex.match(line):
                texts.append(line)
            else:
                sections = re.split(pattern, line)
                texts.extend([x.strip() for x in sections if x])
        return texts

    def detect_profanity(self, texts: List[str]):
        with tracer.start_as_current_span("toxicity: regex for profanity"):
            return [detect_profanity(section) for section in texts]

    def score_harmful_request(self, texts: List[str]):
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
            return self.harmfulrequest_classifier(texts)["prob"]

    def score_toxic_text(self, texts: List[str]):
        """Scores toxicity using toxicity / hate speech classifier

        The pretrained deberta classifier outputs a label of LABEL_1 to represent the presence of toxicity/hate speech
        Arguments:
            texts: List[str]
                parsed sections of text from the original ScoreRequest
        Returns:
            (# texts,) list of toxicity probabilities
        """
        with tracer.start_as_current_span("toxicity: run deberta classifier"):
            # note: a flaw in the model was identified Mar 18 2024
            # it was fine-tuned as a classifier on almost 0 examples of text < 20 chars
            # so for now, we apply repetition padding to the input sequences
            tox_results = self.model(pad_text(texts, type="repetition"))

        toxscores = []
        for l in tox_results:
            for l_ in l:
                if l_["label"].upper() == self.LABEL:
                    toxscores.append(l_["score"])
        return toxscores

    def write_score_details_message(
        self,
        texts: List[str],
        profanity_results: List[bool],
        harmscores: List[float],
        toxscores: List[float],
        threshold: float,
    ):
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
        scores = [np.round(max(x, y), 3) for x, y in zip(harmscores, toxscores)]
        for i, t in sorted(enumerate(texts), key=lambda x: scores[x[0]], reverse=True):
            if profanity_results[i] or scores[i] > threshold:
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
                user_input_tokens=0,
                prompt_tokens=0,
                completion_tokens=0,
            )

        text_sections = self.split_text_into_sections(request.scoring_text)

        # generate rule results & model predictions
        profanity_results = self.detect_profanity(text_sections)
        harmfulrequest_scores = self.score_harmful_request(text_sections)

        # run the toxicity model across sections in parallel
        with utils.TracedThreadPoolExecutor(tracer) as executor:
            toxicity_scores = executor.map(self.score_toxic_text, text_sections)
        max_toxicity_scores = [max(x) for x in list(toxicity_scores)]

        # aggregate rule results & model predictions into the returned RuleScore
        if any(profanity_results):
            # return 0.9999999999... if profanity
            final_score = np.nextafter(1.0, 0.0)
            final_problem_type = ToxicityViolationType.PROFANITY  # Keep them as str
        else:
            # if no profanity, return the maximum score on any section from either of our classifiers
            max_harm, max_tox = max(harmfulrequest_scores), max(max_toxicity_scores)

            final_score = 0.0
            if max_harm > max_tox:
                final_score = max_harm
                final_problem_type = ToxicityViolationType.HARMFUL_REQUEST
            else:
                final_score = max_tox
                final_problem_type = ToxicityViolationType.TOXIC_CONTENT
        bool_result = final_score > request.toxicity_threshold or any(profanity_results)
        genai_engine_results = {False: RuleResultEnum.PASS, True: RuleResultEnum.FAIL}
        genai_engine_result = genai_engine_results[bool_result]
        message = self.write_score_details_message(
            text_sections,
            profanity_results,
            harmfulrequest_scores,
            max_toxicity_scores,
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
