from typing import Annotated
from uuid import UUID

import pandas as pd
from arthur_common.aggregations.aggregator import (
    NumericAggregationFunction,
    SketchAggregationFunction,
)
from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.metrics import DatasetReference, NumericMetric, SketchMetric
from arthur_common.models.schema_definitions import (
    SHIELD_RESPONSE_SCHEMA,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
)
from duckdb import DuckDBPyConnection
from tokencost import calculate_cost_by_tokens


class ShieldInferencePassFailCountAggregation(NumericAggregationFunction):
    METRIC_NAME = "inference_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000001")

    @staticmethod
    def display_name() -> str:
        return "Inference Pass/Fail Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of Shield inferences grouped by the prompt, response, and overall check results."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[NumericMetric]:
        results = ddb_conn.sql(
            f"select time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts, count(*) as count, \
                    result, \
                    inference_prompt.result AS prompt_result, \
                    inference_response.result AS response_result \
                    from {dataset.dataset_table_name} \
                    group by ts, result, prompt_result, response_result \
                    order by ts desc; \
        ",
        ).df()
        group_by_dims = ["result", "prompt_result", "response_result"]
        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            group_by_dims,
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleCountAggregation(NumericAggregationFunction):
    METRIC_NAME = "rule_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000002")

    @staticmethod
    def display_name() -> str:
        return "Rule Result Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of Shield rule evaluations grouped by whether it was on the prompt or response, the rule type, the rule evaluation result, the rule name, and the rule id."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[NumericMetric]:
        results = ddb_conn.sql(
            f" \
            with unnessted_prompt_rules as (select unnest(inference_prompt.prompt_rule_results) as rule, \
                'prompt' as location, \
                time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts \
            from {dataset.dataset_table_name}), \
            unnessted_result_rules as (select unnest(inference_response.response_rule_results) as rule,\
                'response' as location, \
                time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts \
            from {dataset.dataset_table_name}) \
            select ts, \
                count(*) as count, \
                location, \
                rule.rule_type, \
                rule.result, \
                rule.name, \
                rule.id \
            from unnessted_prompt_rules \
            group by ts, location, rule.rule_type, rule.result, rule.name, rule.id \
            UNION ALL \
            select ts, \
                count(*) as count, \
                location, \
                rule.rule_type, \
                rule.result, \
                rule.name, \
                rule.id \
            from unnessted_result_rules \
            group by ts, location, rule.rule_type, rule.result, rule.name, rule.id \
            order by ts desc, location, rule.rule_type, rule.result; \
            ",
        ).df()

        group_by_dims = ["location", "rule_type", "result", "name", "id"]
        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            group_by_dims,
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceHallucinationCountAggregation(NumericAggregationFunction):
    METRIC_NAME = "hallucination_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000003")

    @staticmethod
    def display_name() -> str:
        return "Hallucination Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of Shield hallucination evaluations that failed."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[NumericMetric]:
        results = ddb_conn.sql(
            f" \
            select time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts, \
            count(*) as count \
            from {dataset.dataset_table_name} \
            where length(list_filter(inference_response.response_rule_results, x -> (x.rule_type = 'ModelHallucinationRuleV2' or x.rule_type = 'ModelHallucinationRule') and x.result = 'Fail')) > 0 \
            group by ts \
            order by ts desc; \
        ",
        ).df()

        series = [
            self.dimensionless_query_results_to_numeric_metrics(results, "count", "ts"),
        ]
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleToxicityScoreAggregation(SketchAggregationFunction):
    METRIC_NAME = "toxicity_score"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000004")

    @staticmethod
    def display_name() -> str:
        return "Toxicity Distribution"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on toxicity scores returned by the Shield toxicity rule."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f"\
                with unnested_prompt_results as (select to_timestamp(created_at / 1000) as ts, \
                    unnest(inference_prompt.prompt_rule_results) as rule_results, \
                    'prompt' as location \
                from {dataset.dataset_table_name}), \
                unnested_response_results as (select to_timestamp(created_at / 1000) as ts, \
                        unnest(inference_response.response_rule_results) as rule_results, \
                        'response' as location \
                from {dataset.dataset_table_name}) \
                select ts as timestamp, \
                    rule_results.details.toxicity_score::DOUBLE as toxicity_score, \
                    rule_results.result as result, \
                    location \
                from unnested_prompt_results \
                where rule_results.details.toxicity_score IS NOT NULL \
                UNION ALL \
                select ts as timestamp, \
                    rule_results.details.toxicity_score::DOUBLE as toxicity_score, \
                    rule_results.result as result, \
                    location \
                from unnested_response_results \
                where rule_results.details.toxicity_score IS NOT NULL \
                order by ts desc;    \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "toxicity_score",
            ["result", "location"],
            "timestamp",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRulePIIDataScoreAggregation(SketchAggregationFunction):
    METRIC_NAME = "pii_score"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000005")

    @staticmethod
    def display_name() -> str:
        return "PII Score Distribution"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on PII scores returned by the Shield PII rule."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f"\
with unnested_prompt_results as (select time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts,                    \
                                        unnest(inference_prompt.prompt_rule_results)                       as rule_results,          \
                                        'prompt'                                                           as location               \
                                 from {dataset.dataset_table_name}),                                                                                         \
     unnested_response_results as (select time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts,                  \
                                          unnest(inference_response.response_rule_results)                   as rule_results,        \
                                          'response'                                                         as location             \
                                   from {dataset.dataset_table_name}),                                                                                       \
     unnested_entites as (select ts,                                                                                                 \
                                 rule_results.result,                                                                                \
                                 rule_results.rule_type,                                                                             \
                                 location,                                                                                           \
                                 unnest(rule_results.details.pii_entities) as pii_entity                                             \
                          from unnested_response_results                                                                             \
                          where rule_results.rule_type = 'PIIDataRule'                                                               \
                                                                                                                                     \
                          UNION ALL                                                                                                  \
                                                                                                                                     \
                          select ts,                                                                                                 \
                                 rule_results.result,                                                                                \
                                 rule_results.rule_type,                                                                             \
                                 location,                                                                                           \
                                 unnest(rule_results.details.pii_entities) as pii_entity                                             \
                          from unnested_prompt_results                                                                               \
                          where rule_results.rule_type = 'PIIDataRule')                                                              \
select ts as timestamp, result, rule_type, location, TRY_CAST(pii_entity.confidence AS FLOAT) as pii_score, pii_entity.entity as entity                 \
from unnested_entites                                                                                                                \
order by ts desc;                                                                                                                    \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "pii_score",
            ["result", "location", "entity"],
            "timestamp",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleClaimCountAggregation(SketchAggregationFunction):
    METRIC_NAME = "claim_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000006")

    @staticmethod
    def display_name() -> str:
        return "Claim Count Distribution - All Claims"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on over the number of claims identified by the Shield hallucination rule."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f"\
                with unnested_results as (select to_timestamp(created_at / 1000) as ts, \
                                        unnest(inference_response.response_rule_results) as rule_results \
                                        from {dataset.dataset_table_name}) \
                select ts as timestamp, \
                    length(rule_results.details.claims) as num_claims, \
                    rule_results.result as result \
                from unnested_results \
                where rule_results.rule_type = 'ModelHallucinationRuleV2' \
                and rule_results.result != 'Skipped' \
                order by ts desc; \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "num_claims",
            ["result"],
            "timestamp",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleClaimPassCountAggregation(SketchAggregationFunction):
    METRIC_NAME = "claim_valid_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000007")

    @staticmethod
    def display_name() -> str:
        return "Claim Count Distribution - Valid Claims"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on the number of valid claims determined by the Shield hallucination rule."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f"\
                with unnested_results as (select to_timestamp(created_at / 1000) as ts, \
                                        unnest(inference_response.response_rule_results) as rule_results \
                                        from {dataset.dataset_table_name}) \
                select ts as timestamp, \
                    length(list_filter(rule_results.details.claims, x -> x.valid)) as num_valid_claims, \
                    rule_results.result as result \
                from unnested_results \
                where rule_results.rule_type = 'ModelHallucinationRuleV2' \
                and rule_results.result != 'Skipped' \
                order by ts desc; \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "num_valid_claims",
            ["result"],
            "timestamp",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleClaimFailCountAggregation(SketchAggregationFunction):
    METRIC_NAME = "claim_invalid_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000008")

    @staticmethod
    def display_name() -> str:
        return "Claim Count Distribution - Invalid Claims"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on the number of invalid claims determined by the Shield hallucination rule."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f"\
                with unnested_results as (select to_timestamp(created_at / 1000) as ts, \
                                        unnest(inference_response.response_rule_results) as rule_results \
                                        from {dataset.dataset_table_name}) \
                select ts as timestamp, \
                    length(list_filter(rule_results.details.claims, x -> not x.valid)) as num_failed_claims, \
                    rule_results.result as result \
                from unnested_results \
                where rule_results.rule_type = 'ModelHallucinationRuleV2' \
                and rule_results.result != 'Skipped' \
                order by ts desc; \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "num_failed_claims",
            ["result"],
            "timestamp",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceRuleLatencyAggregation(SketchAggregationFunction):
    METRIC_NAME = "rule_latency"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000009")

    @staticmethod
    def display_name() -> str:
        return "Rule Latency Distribution"

    @staticmethod
    def description() -> str:
        return "Metric that reports a distribution (data sketch) on the latency of Shield rule evaluations. Dimensions are the rule result, rule type, and whether the rule was applicable to a prompt or response."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[SketchMetric]:
        results = ddb_conn.sql(
            f" \
            with unnested_prompt_rules as (select unnest(inference_prompt.prompt_rule_results) as rule, \
                'prompt' as location, \
                to_timestamp(created_at / 1000) as ts, \
            from {dataset.dataset_table_name}), \
            unnested_response_rules as (select unnest(inference_response.response_rule_results) as rule,\
                'response' as location, \
                to_timestamp(created_at / 1000) as ts, \
            from {dataset.dataset_table_name}) \
            select ts, \
                location, \
                rule.rule_type, \
                rule.result, \
                rule.latency_ms \
            from unnested_prompt_rules \
            UNION ALL \
            select ts, \
                location, \
                rule.rule_type, \
                rule.result, \
                rule.latency_ms \
            from unnested_response_rules \
            ",
        ).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            "latency_ms",
            ["result", "rule_type", "location"],
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]


class ShieldInferenceTokenCountAggregation(NumericAggregationFunction):
    METRIC_NAME = "token_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000021")

    @staticmethod
    def display_name() -> str:
        return "Token Count"

    @staticmethod
    def description() -> str:
        return "Metric that reports the number of tokens in the Shield response and prompt schemas, and their estimated cost."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The task inference dataset sourced from Arthur Shield.",
                model_problem_type=ModelProblemType.ARTHUR_SHIELD,
            ),
        ],
        # This parameter exists mostly to work with the aggregation matcher such that we don't need to have any special handling for shield
        shield_response_column: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    SHIELD_RESPONSE_SCHEMA,
                ],
                friendly_name="Shield Response Column",
                description="The Shield response column from the task inference dataset.",
            ),
        ],
    ) -> list[NumericMetric]:
        results = ddb_conn.sql(
            f" \
            select \
                time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts, \
                COALESCE(sum(inference_prompt.tokens), 0) as tokens, \
                'prompt' as location \
            from {dataset.dataset_table_name} \
            group by time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)), location \
            UNION ALL \
            select \
                time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)) as ts, \
                COALESCE(sum(inference_response.tokens), 0) as tokens, \
                'response' as location \
            from {dataset.dataset_table_name}  \
            group by time_bucket(INTERVAL '5 minutes', to_timestamp(created_at / 1000)), location; \
            ",
        ).df()

        series = self.group_query_results_to_numeric_metrics(
            results,
            "tokens",
            ["location"],
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        resp = [metric]

        # Compute Cost for each model
        models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "o1-mini",
            "deepseek-chat",
            "claude-3-5-sonnet-20241022",
            "gemini/gemini-1.5-pro",
            "meta.llama3-1-8b-instruct-v1:0",
            "meta.llama3-1-70b-instruct-v1:0",
            "meta.llama3-2-11b-instruct-v1:0",
        ]

        # Precompute input/output classification to avoid recalculating in loop
        location_type = results["location"].apply(
            lambda x: "input" if x == "prompt" else "output",
        )

        for model in models:
            # Efficient list comprehension instead of apply
            cost_values = [
                calculate_cost_by_tokens(int(tokens), model, loc_type)
                for tokens, loc_type in zip(results["tokens"], location_type)
            ]

            model_df = pd.DataFrame(
                {
                    "ts": results["ts"],
                    "cost": cost_values,
                    "location": results["location"],
                },
            )

            model_series = self.group_query_results_to_numeric_metrics(
                model_df,
                "cost",
                ["location"],
                "ts",
            )
            resp.append(self.series_to_metric(f"token_cost.{model}", model_series))
        return resp
