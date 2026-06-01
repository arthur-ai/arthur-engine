import os

from arthur_common.models.llm_model_providers import (
    JsonPropertySchema,
    JsonSchema,
    LLMTool,
    MessageRole,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
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
from utils.file_parsing import parse_csv_rows

DEMO_TASK_DATASET_CSV_PATH = os.path.join(os.path.dirname(__file__), "DemoDataset.csv")

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

DEMO_TASK_SYSTEM_PROMPT = (
    "You are a general knowledge assistant. "
    "All your answers should be respectful and concise. All answers should be two sentences or less. "
    "You should assume the user is 5 years old and respond to the user accordingly. "
    "The question to answer is: {{query}}\n\n"
    "Use the following tools to answer users' questions:\n\n"
    "- wikipedia_search(query): Search Wikipedia for a topic and return a list of matching article titles.\n"
    "- wikipedia_fetch(title): Fetch the full summary of a specific Wikipedia article by title.\n\n"
    "Use wikipedia_search first to find the most relevant article title, then call wikipedia_fetch with "
    "that title to read the summary before answering. If you already fetched data and still have it in "
    "your memory, you do not need to fetch it again."
)

DEMO_TASK_ANSWER_RELEVANCE_EVAL_PROMPT = (
    "Given user's message and assistant's response:\n\n"
    "<user_message>\n"
    "{{query}}\n"
    "</user_message>\n\n"
    "<assistant_response>\n"
    "{{response}}\n"
    "</assistant_response>\n\n"
    "Determine if the assistant's response is relevant to the user's message. "
    "Respond with 1 if it is and 0 if it is not. "
    "Ignore all formatting, structure, and metadata (e.g. markdown, json, tool calls, API responses, etc.) — "
    "extract and evaluate only the natural language text content within. "
    "You should never fail or pass anything based on if it was a json object, if there were tool calls, "
    "or anything similar. You should also make no reference to the format of the response or "
    '"natural language content", just give the reasoning.\n'
)

DEMO_TASK_ANSWER_RELEVANCE_EVAL_TRANSFORM = NewTraceTransformRequest(
    name="Answer Relevance Eval",
    description="Evaluates if the assistant's response is relevant to the user's input",
    definition=TraceTransformDefinition(
        variables=[
            TraceTransformVariableDefinition(
                variable_name="query",
                span_name="chatbot",
                attribute_path="attributes.input.value.-1.content",
            ),
            TraceTransformVariableDefinition(
                variable_name="response",
                span_name="chatbot",
                attribute_path="attributes.output.value.text",
            ),
        ],
    ),
)


DEMO_TASK_CONCISENESS_EVAL_PROMPT = (
    "Given a response, determine if the response is concise. "
    "Respond with a 1 if the response is two sentences or less and 0 if it is longer. "
    "Ignore all formatting, structure, and metadata (e.g. markdown, json, tool calls, API responses, etc.) — "
    "extract and evaluate only the natural language text content within. "
    "You should never fail or pass anything based on if it was a json object, if there were tool calls, "
    "or anything similar. You should also make no reference to the format of the response or "
    '"natural language content", just give the reasoning.\n\n'
    "response:\n"
    "{{response}}\n"
)


DEMO_TASK_READABILITY_EVAL_PROMPT = (
    "Given a response, determine if the response is readable. "
    "A response is considered readable if it is between an 8th-12th grade level of readability. "
    "If it is too low or too high, it is considered not readable. "
    "Ignore all formatting, structure, and metadata (e.g. markdown, json, tool calls, API responses, etc.) — "
    "extract and evaluate only the natural language text content within. "
    "You should never fail or pass anything based on if it was a json object, if there were tool calls, "
    "or anything similar. You should also make no reference to the format of the response or "
    '"natural language content", just give the reasoning.\n\n'
    "Respond with a 1 if the response is readable and 0 if it is not.\n\n"
    "response:\n"
    "{{response}}\n"
)

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
    description="General knowledge query/response pairs and wikipedia search/fetch results.",
)

DEMO_TASK_DATASET_ROWS = parse_csv_rows(DEMO_TASK_DATASET_CSV_PATH)

DEMO_TASK_DATASET_VERSION_REQUEST = NewDatasetVersionRequest(
    rows_to_add=[
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name=column_name,
                    column_value=column_value,
                )
                for column_name, column_value in row.items()
            ],
        )
        for row in DEMO_TASK_DATASET_ROWS
    ],
    rows_to_delete=[],
    rows_to_update=[],
)


DEMO_TASK_PROMPT_MESSAGES = [
    OpenAIMessage(
        role=MessageRole.SYSTEM,
        content=DEMO_TASK_SYSTEM_PROMPT,
    ),
    OpenAIMessage(
        role=MessageRole.AI,
        tool_calls=[
            ToolCall(
                id="wiki_search",
                function=ToolCallFunction(
                    name="wikipedia_search",
                    arguments='{"query":"{{search_query}}"}',
                ),
            ),
        ],
    ),
    OpenAIMessage(
        role=MessageRole.TOOL,
        tool_call_id="wiki_search",
        content="{{search_results}}",
    ),
    OpenAIMessage(
        role=MessageRole.AI,
        tool_calls=[
            ToolCall(
                id="wiki_fetch",
                function=ToolCallFunction(
                    name="wikipedia_fetch",
                    arguments='{"title":"{{fetch_query}}"}',
                ),
            ),
        ],
    ),
    OpenAIMessage(
        role=MessageRole.TOOL,
        tool_call_id="wiki_fetch",
        content="{{fetch_results}}",
    ),
]
