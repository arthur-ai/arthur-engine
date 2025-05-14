RESPONSE_RELEVANCE_PROMPT_TEMPLATE = """
You are an AI assistant that checks whether a LLM response is relevant to and within the scope of a given system prompt and user query. The system prompt could describe a persona or character that the assistant is acting as, and the user query is executed within the system prompt.
If the LLM response is within the realm of possibility described by system prompt and relevant to the user query, provide a score of 1. If the response is not relevant, provide a score of 0. If the user
query is unsafe or unethical, please respond with 0 and offer justification for unethical request.

### System Prompt:
{system_prompt}

### User Query:
{user_query}

### LLM Response:
{llm_response}

### Task:
Evaluate if the LLM response is relevant to the system prompt and the user query. Provide a response in the following format:

- **Relevance Score (0-1)**: A numerical value where 1 means "highly relevant" and 0 means "completely irrelevant."
- **Justification**: Explain why the response is relevant or not.
- **Suggested Refinement (if needed)**: If the response is somewhat relevant but not fully aligned, suggest a better phrasing.

{format_instructions}
""" 

USER_QUERY_RELEVANCE_PROMPT_TEMPLATE = """
You are an AI assistant that checks whether a user query is relevant to and within the scope of a given system prompt. The system prompt could describe a persona or character that the assistant is acting as.
If the user query is within the realm of possibility described by system prompt, provide a score of 1. The query does not need to be exact match to the system prompt. If the query is not relevant, provide a score of 0.

### System Prompt:
{system_prompt}

### User Query:
{user_query}

### Task:
Evaluate if the user query is relevant to the system prompt. Provide a response in the following format:

- **Relevance Score (0-1)**: A numerical value where 1 means "highly relevant" and 0 means "completely irrelevant."
- **Justification**: Explain why the query is relevant or not.
- **Suggested Refinement (if needed)**: If the query is somewhat relevant but not fully aligned, suggest a better phrasing.

{format_instructions}
"""