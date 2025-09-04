from typing import Optional, Union

from arthur_client.api_bindings import Config, RuleResponseConfig
from arthur_client.api_bindings.models import ExampleConfig as ScopeExampleConfig
from arthur_client.api_bindings.models import ExamplesConfig as ScopeExamplesConfig
from arthur_client.api_bindings.models import KeywordsConfig as ScopeKeywordsConfig
from arthur_client.api_bindings.models import (
    MetricResponse as ScopeClientMetricResponse,
)
from arthur_client.api_bindings.models import MetricType as ScopeMetricType
from arthur_client.api_bindings.models import PIIConfig as ScopePIIConfig
from arthur_client.api_bindings.models import RegexConfig as ScopeRegexConfig
from arthur_client.api_bindings.models import RuleResponse as ScopeClientRuleResponse
from arthur_client.api_bindings.models import RuleScope as ScopeRuleScope
from arthur_client.api_bindings.models import RuleType as ScopeRuleType
from arthur_client.api_bindings.models import TaskResponse as ScopeClientTaskResponse
from arthur_client.api_bindings.models import ToxicityConfig as ScopeToxicityConfig

from arthur_common.models.common_schemas import ExamplesConfig as ApiExamplesConfig
from arthur_common.models.common_schemas import KeywordsConfig as ApiKeywordsConfig
from arthur_common.models.common_schemas import PIIConfig as ApiPIIConfig
from arthur_common.models.common_schemas import RegexConfig as ApiRegexConfig
from arthur_common.models.common_schemas import ToxicityConfig as ApiToxicityConfig
from arthur_common.models.enums import MetricType as ApiMetricType
from arthur_common.models.metric_schemas import (
    RelevanceMetricConfig as ApiRelevanceMetricConfig,
)
from arthur_common.models.request_schemas import NewMetricRequest as ApiNewMetricRequest
from arthur_common.models.request_schemas import NewRuleRequest as ApiNewRuleRequest
from arthur_common.models.response_schemas import MetricResponse as ApiMetricResponse
from arthur_common.models.response_schemas import RuleResponse as ApiRuleResponse
from arthur_common.models.response_schemas import TaskResponse as ApiTaskResponse

from genai_client import Config
from genai_client.models import ExampleConfig as ShieldExampleConfig
from genai_client.models import ExamplesConfig as ShieldExamplesConfig
from genai_client.models import KeywordsConfig as ShieldKeywordsConfig
from genai_client.models import MetricType as ShieldMetricType
from genai_client.models import NewApiKeyRequest as ShieldNewApiKeyRequest
from genai_client.models import NewMetricRequest as ShieldNewMetricRequest
from genai_client.models import NewRuleRequest as ShieldNewRuleRequest
from genai_client.models import PIIConfig as ShieldPIIConfig
from genai_client.models import RegexConfig as ShieldRegexConfig
from genai_client.models import RelevanceMetricConfig as ShieldRelevanceMetricConfig
from genai_client.models import RuleType as ShieldRuleType
from genai_client.models import ToxicityConfig as ShieldToxicityConfig

ApiConfigTypes = Optional[
    Union[
        ApiKeywordsConfig,
        ApiRegexConfig,
        ApiExamplesConfig,
        ApiToxicityConfig,
        ApiPIIConfig,
        ApiNewMetricRequest,
        ApiMetricType,
    ]
]

ShieldConfigTypes = Optional[
    Union[
        ShieldKeywordsConfig,
        ShieldRegexConfig,
        ShieldExamplesConfig,
        ShieldToxicityConfig,
        ShieldPIIConfig,
        ShieldRelevanceMetricConfig,
        ShieldNewMetricRequest,
        ShieldMetricType,
        ShieldNewApiKeyRequest,
    ]
]
ScopeConfigTypes = Optional[
    Union[
        ScopeKeywordsConfig,
        ScopeRegexConfig,
        ScopeExamplesConfig,
        ScopeToxicityConfig,
        ScopePIIConfig,
    ]
]


class ShieldClientTypeConverter:

    @classmethod
    def rule_config_api_to_shield_client(cls, api: ApiConfigTypes) -> ShieldConfigTypes:
        if api is None:
            return None

        if isinstance(api, ApiKeywordsConfig):
            return ShieldKeywordsConfig(
                keywords=api.keywords,
            )
        elif isinstance(api, ApiRegexConfig):
            return ShieldRegexConfig(
                regex_patterns=api.regex_patterns,
            )
        elif isinstance(api, ApiExamplesConfig):
            return ShieldExamplesConfig(
                examples=[
                    ShieldExampleConfig(
                        example=a.example,
                        result=a.result,
                    )
                    for a in api.examples
                ],
                hint=api.hint,
            )
        elif isinstance(api, ApiToxicityConfig):
            return ShieldToxicityConfig(
                threshold=api.threshold,
            )
        elif isinstance(api, ApiPIIConfig):
            return ShieldPIIConfig(
                disabled_pii_entities=api.disabled_pii_entities,
                confidence_threshold=api.confidence_threshold,
                allow_list=api.allow_list,
            )
        else:
            raise ValueError(f"Unknown API rule config type: {type(api)}")

    @classmethod
    def new_rule_request_api_to_shield_client(
        cls, api: ApiNewRuleRequest
    ) -> ShieldNewRuleRequest:
        return ShieldNewRuleRequest(
            name=api.name,
            type=ShieldRuleType(api.type),
            apply_to_prompt=api.apply_to_prompt,
            apply_to_response=api.apply_to_response,
            config=Config(cls.rule_config_api_to_shield_client(api.config)),
        )

    @classmethod
    def relevance_metric_config_api_to_shield_client(
        cls, api: ApiRelevanceMetricConfig
    ) -> ShieldRelevanceMetricConfig:
        return ShieldRelevanceMetricConfig(
            relevance_threshold=api.relevance_threshold,
            use_llm_judge=api.use_llm_judge,
        )

    @classmethod
    def new_metric_request_api_to_shield_client(
        cls, api: ApiNewMetricRequest
    ) -> ShieldNewMetricRequest:
        config = None
        if api.config is not None:
            config = cls.relevance_metric_config_api_to_shield_client(api.config)

        return ShieldNewMetricRequest(
            name=api.name,
            type=ShieldMetricType(api.type),
            metric_metadata=api.metric_metadata,
            config=config,
        )


class ScopeClientTypeConverter:

    @classmethod
    def task_response_api_to_scope_client(
        cls, api: ApiTaskResponse
    ) -> ScopeClientTaskResponse:
        return ScopeClientTaskResponse(
            id=api.id,
            name=api.name,
            created_at=api.created_at,
            updated_at=api.updated_at,
            is_agentic=api.is_agentic,
            rules=[cls.rule_response_api_to_scope_client(r) for r in api.rules],
            metrics=(
                [cls.metric_response_api_to_scope_client(m) for m in api.metrics]
                if api.metrics
                else []
            ),
        )

    @classmethod
    def metric_response_api_to_scope_client(
        cls, api: ApiMetricResponse
    ) -> ScopeClientMetricResponse:
        return ScopeClientMetricResponse(
            id=api.id,
            name=api.name,
            type=ScopeMetricType(api.type),
            metric_metadata=api.metric_metadata,
            config=api.config,
            created_at=api.created_at,
            updated_at=api.updated_at,
            enabled=api.enabled,
        )

    @classmethod
    def rule_response_api_to_scope_client(
        cls, api: ApiRuleResponse
    ) -> ScopeClientRuleResponse:
        return ScopeClientRuleResponse(
            id=api.id,
            name=api.name,
            type=ScopeRuleType(api.type),
            apply_to_prompt=api.apply_to_prompt,
            apply_to_response=api.apply_to_response,
            enabled=api.enabled,
            scope=ScopeRuleScope(api.scope),
            created_at=api.created_at,
            updated_at=api.updated_at,
            config=RuleResponseConfig(cls.rule_config_api_to_scope_client(api.config)),
        )

    @classmethod
    def rule_config_api_to_scope_client(cls, api: ApiConfigTypes) -> ScopeConfigTypes:
        if api is None:
            return None

        if isinstance(api, ApiKeywordsConfig):
            return ScopeKeywordsConfig(
                keywords=api.keywords,
            )
        elif isinstance(api, ApiRegexConfig):
            return ScopeRegexConfig(
                regex_patterns=api.regex_patterns,
            )
        elif isinstance(api, ApiExamplesConfig):
            return ScopeExamplesConfig(
                examples=[
                    ScopeExampleConfig(
                        example=a.example,
                        result=a.result,
                    )
                    for a in api.examples
                ],
                hint=api.hint,
            )
        elif isinstance(api, ApiToxicityConfig):
            return ScopeToxicityConfig(
                threshold=api.threshold,
            )
        elif isinstance(api, ApiPIIConfig):
            return ScopePIIConfig(
                disabled_pii_entities=api.disabled_pii_entities,
                confidence_threshold=api.confidence_threshold,
                allow_list=api.allow_list,
            )
        else:
            raise ValueError(f"Unknown API rule config type: {type(api)}")
