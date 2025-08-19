import re
import uuid
from typing import Callable

from db_models.db_models import DatabaseRuleData
from fastapi import HTTPException
from pydantic import BaseModel
from arthur_common.models.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from arthur_common.models.enums import RuleDataType, RuleType
from utils.utils import constants


class RuleData(BaseModel):
    id: str
    data_type: RuleDataType
    data: str

    def _to_database_model(self):
        return DatabaseRuleData(id=self.id, data_type=self.data_type, data=self.data)

    @staticmethod
    def _from_database_model(x: DatabaseRuleData):
        return RuleData(id=x.id, data_type=x.data_type, data=x.data)


def get_regex_config(config: RegexConfig) -> list[RuleData]:
    if not isinstance(config, RegexConfig):
        raise HTTPException(
            status_code=400,
            detail="Regex rule type must have a RegexConfig",
        )
    if not config.regex_patterns:
        raise HTTPException(
            status_code=400,
            detail="regex_patterns must be provided",
        )

    rule_configurations: list[RuleData] = []
    for pattern in config.regex_patterns:
        try:
            re.compile(pattern)
        except:
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_INVALID_REGEX % pattern,
            )
        rule_configurations.append(
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.REGEX,
                data=pattern,
            ),
        )
    return rule_configurations


def get_keyword_config(config: KeywordsConfig) -> list[RuleData]:
    if not isinstance(config, KeywordsConfig):
        raise HTTPException(
            status_code=400,
            detail="Keywords rule type must have a KeywordConfig",
        )
    rule_configurations = [
        RuleData(
            id=str(uuid.uuid4()),
            data_type=RuleDataType.KEYWORD,
            data=keyword,
        )
        for keyword in config.keywords
    ]
    return rule_configurations


def get_model_sensitive_data_config(config: ExamplesConfig) -> list[RuleData]:
    if not isinstance(config, ExamplesConfig):
        raise HTTPException(
            status_code=400,
            detail="Model Sensitive Data rule type must have example config",
        )

    rule_configurations: list[RuleData] = [
        RuleData(
            id=str(uuid.uuid4()),
            data_type=RuleDataType.JSON,
            data=example.model_dump_json(),
        )
        for example in config.examples
    ]
    if config.hint:
        rule_configurations.append(
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.HINT,
                data=str(config.hint),
            ),
        )

    return rule_configurations


def get_pii_data_config(config: PIIConfig) -> list[RuleData]:
    if not isinstance(config, PIIConfig):
        raise HTTPException(
            status_code=400,
            detail="PII rule type must have a PIIConfig",
        )

    rule_configurations: list[RuleData] = []
    if config.confidence_threshold:
        rule_configurations.append(
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.PII_THRESHOLD,
                data=str(config.confidence_threshold),
            ),
        )

    if config.disabled_pii_entities:
        rule_configurations.append(
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.PII_DISABLED_PII,
                data=",".join(config.disabled_pii_entities),
            ),
        )

    if config.allow_list:
        rule_configurations.append(
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.PII_ALLOW_LIST,
                data=",".join(config.allow_list),
            ),
        )
    return rule_configurations


def get_toxicity_config(config: ToxicityConfig) -> list[RuleData]:
    if not isinstance(config, ToxicityConfig):
        raise HTTPException(
            status_code=400,
            detail="Toxicity rule type must have a ToxicityConfig",
        )
    return [
        RuleData(
            id=str(uuid.uuid4()),
            data_type=RuleDataType.TOXICITY_THRESHOLD,
            data=str(config.threshold),
        ),
    ]


CONFIG_CHECKERS: dict[
    str
    | Callable[
        [RegexConfig | KeywordsConfig | ToxicityConfig | PIIConfig | ExamplesConfig],
        list[RuleData],
    ]
] = {
    RuleType.REGEX.value: get_regex_config,
    RuleType.KEYWORD.value: get_keyword_config,
    RuleType.MODEL_SENSITIVE_DATA.value: get_model_sensitive_data_config,
    RuleType.MODEL_HALLUCINATION_V2.value: lambda x: [],
    RuleType.PROMPT_INJECTION.value: lambda x: [],
    RuleType.PII_DATA.value: get_pii_data_config,
    RuleType.TOXICITY.value: get_toxicity_config,
}
