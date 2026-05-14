from arthur_common.models.task_eval_schemas import (
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
)

from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.internal_schemas import NewTraceTransformRequest
from schemas.request_schemas import NewDatasetRequest, NewDatasetVersionRequest

DEMO_TASK_SYSTEM_PROMPT = """
You are a general knowledge assistant. All your answers should be respectful and concise. All answers should be two sentences or less."""

DEMO_TASK_PROMPT_ADHERENCE_EVAL_PROMPT = """Given a list of input and output messages:

<input_messages>
{{input_messages}}
</input_messages>

<output_messages>
{{output_messages}}
</output_messages>

Determine if the assistant's final response adheres to the prompt. Respond with 1 if it does and 0 if it does not.
"""

DEMO_TASK_PROMPT_ADHERENCE_EVAL_TRANSFORM = NewTraceTransformRequest(
    name="Prompt Adherence Eval",
    description="Evaluates if the assistant's final response adheres to the prompt.",
    definition=TraceTransformDefinition(
        variables=[
            TraceTransformVariableDefinition(
                variable_name="input_messages",
                span_name="llm_call",
                attribute_path="attributes.llm.input_messages",
            ),
            TraceTransformVariableDefinition(
                variable_name="output_messages",
                span_name="llm_call",
                attribute_path="attributes.llm.output_messages",
            ),
        ],
    ),
)


# NOTE: This eval is meant to be incorrect so users can see a failing eval and try
# to come up with a plan to fix it.
DEMO_TASK_CONCISENESS_EVAL_PROMPT = """Given a response, determine if the response is concise.
Respond with a 0 if the response is two sentences or less and 1 if it is longer.

response:
{{response}}
"""

DEMO_TASK_CONCISENESS_EVAL_TRANSFORM = NewTraceTransformRequest(
    name="Conciseness Eval",
    description="Evaluates if the response is concise.",
    definition=TraceTransformDefinition(
        variables=[
            TraceTransformVariableDefinition(
                variable_name="response",
                span_name="llm_call",
                attribute_path="attributes.llm.output_messages",
            ),
        ],
    ),
)


DEMO_TASK_DATASET_REQUEST = NewDatasetRequest(
    name="Demo Dataset",
    description="Genreal knowledge query/response pairs.",
)

DEMO_TASK_DATASET_ROWS = [
    ("What is the capital of Australia?", "Canberra"),
    ("How many sides does a hexagon have?", "6 sides"),
    ("What planet is known as the Red Planet?", "Mars"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
    ("What is the chemical symbol for gold?", "Au"),
    ("How many bones are in the adult human body?", "206 bones"),
    ("What is the largest ocean on Earth?", "The Pacific Ocean"),
    ("In what year did World War II end?", "1945"),
    ("What is the fastest land animal?", "The cheetah"),
    ("How many continents are there on Earth?", "7 continents"),
]

DEMO_TASK_DATASET_VERSION_REQUEST = NewDatasetVersionRequest(
    rows_to_add=[
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="query",
                    column_value=query,
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="response",
                    column_value=response,
                ),
            ],
        )
        for query, response in DEMO_TASK_DATASET_ROWS
    ],
    rows_to_delete=[],
    rows_to_update=[],
)
