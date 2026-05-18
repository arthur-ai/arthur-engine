from arthur_common.models.llm_model_providers import (
    JsonPropertySchema,
    JsonSchema,
    LLMTool,
    ToolFunction,
)
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

WIKIPEDIA_SEARCH_TOOL = LLMTool(
    function=ToolFunction(
        name="wikipedia_search",
        description="Search Wikipedia for a topic and return a list of matching article titles.",
        parameters=JsonSchema(
            properties={
                "query": JsonPropertySchema(type="string"),
            },
            required=["query"],
        ),
    ),
)

WIKIPEDIA_FETCH_TOOL = LLMTool(
    function=ToolFunction(
        name="wikipedia_fetch",
        description="Fetch the full summary of a specific Wikipedia article by title.",
        parameters=JsonSchema(
            properties={
                "title": JsonPropertySchema(type="string"),
            },
            required=["title"],
        ),
    ),
)

DEMO_TASK_TOOLS = [WIKIPEDIA_SEARCH_TOOL, WIKIPEDIA_FETCH_TOOL]

DEMO_TASK_SYSTEM_PROMPT = """
You are a general knowledge assistant. All your answers should be respectful and concise. All answers should be two sentences or less.
You should assume the user is 5 years old and respond to the user accordingly.

You have access to the following tools to look up information when you are unsure or need to verify a fact:
- wikipedia_search(query): Search Wikipedia for a topic and return a list of matching article titles.
- wikipedia_fetch(title): Fetch the full summary of a specific Wikipedia article by title.

Use wikipedia_search first to find the most relevant article title, then call wikipedia_fetch with that title to read the summary before answering. If you already fetched data and still have it in your memory, you do not need to fetch it again.
"""

DEMO_TASK_ANSWER_RELEVANCE_EVAL_PROMPT = """Given a list of input and output messages:

<input_messages>
{{input_messages}}
</input_messages>

<output_messages>
{{output_messages}}
</output_messages>

Determine if the assistant's response is relevant to the input messages. Respond with 1 if it is and 0 if it is not.
Ignore all formatting, structure, and metadata (e.g. markdown, json, tool calls, API responses, etc.) — extract and
evaluate only the natural language text content within. You should never fail or pass anything based on if it was a
json object, if there were tool calls, or anything similar. You should also make no reference to the format of the
response or "natural language content", just give the reasoning.
"""

DEMO_TASK_ANSWER_RELEVANCE_EVAL_TRANSFORM = NewTraceTransformRequest(
    name="Answer Relevance Eval",
    description="Evaluates if the assistant's response is relevant to the user's input",
    definition=TraceTransformDefinition(
        variables=[
            TraceTransformVariableDefinition(
                variable_name="input_messages",
                span_name="chatbot",
                attribute_path="attributes.input.value",
            ),
            TraceTransformVariableDefinition(
                variable_name="output_messages",
                span_name="chatbot",
                attribute_path="attributes.output.value.text",
            ),
        ],
    ),
)


DEMO_TASK_CONCISENESS_EVAL_PROMPT = """Given a response, determine if the response is concise.
Respond with a 1 if the response is two sentences or less and 0 if it is longer. Ignore all formatting, structure, and
metadata (e.g. markdown, json, tool calls, API responses, etc.) — extract and evaluate only the
natural language text content within. You should never fail or pass anything based on if it was a json object, if there
were tool calls, or anything similar. You should also make no reference to the format of the response or "natural language content",
just give the reasoning.

response:
{{response}}
"""


DEMO_TASK_READABILITY_EVAL_PROMPT = """Given a response, determine if the response is readable.w
A response is considered readable if it is between an 8th-12th grade level of readability. If
it is too low or too high, it is considered not readable. Ignore all formatting, structure, and
metadata (e.g. markdown, json, tool calls, API responses, etc.) — extract and evaluate only the
natural language text content within. You should never fail or pass anything based on if it was
a json object, if there were tool calls, or anything similar. You should also make no reference
to the format of the response or "natural language content", just give the reasoning.

Respond with a 1 if the response is readable and 0 if it is not.

response:
{{response}}
"""

DEMO_TASK_RESPONSE_EXTRACTION_TRANSFORM = NewTraceTransformRequest(
    name="Response Extraction Transform",
    description="Extracts the response from a trace",
    definition=TraceTransformDefinition(
        variables=[
            TraceTransformVariableDefinition(
                variable_name="response",
                span_name="chatbot",
                attribute_path="attributes.output.value.text",
            ),
        ],
    ),
)

DEMO_TASK_DATASET_REQUEST = NewDatasetRequest(
    name="Demo Dataset",
    description="General knowledge query/response pairs.",
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
    (
        "What is machine learning?",
        "Empirical risk minimization over a hypothesis space via gradient-based optimization.",
    ),
    (
        "How does the stock market work?",
        "A continuous double auction where prices emerge from stochastic order flow under the efficient market hypothesis.",
    ),
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
