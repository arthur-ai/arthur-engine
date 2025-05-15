TOOL_SELECTION_PROMPT_TEMPLATE = """
    You are tasked with evaluating whether an AI agent correctly selected a tool to respond to a user's question. You do **not** need to evaluate how the tool was used—only whether the correct tool was selected.

    **Inputs:**
    - **System Prompt:** Instructions, constraints, and available tools for the AI agent.
    - **User Question:** The input provided by the user.
    - **Context:** The full chat history, including any prior tool calls and responses.

    ---
    ### **Your Task:**
    Analyze the provided information and evaluate whether the AI agent:

    **Tool Selection**
    - **0**: Tool Selection Incorrect (The wrong tool(s) were selected for the job)
    - **1**: Tool Selection Correct (The right tool(s) were selected for the job)
    - **2**: No Tool Selected/Tool Not Available (A tool was not available or the assistant did not use a tool)

    **IMPORTANT:**
    - Ignore the arguments or parameters passed to the tool; only determine whether the selected tool was appropriate for the task.
    - If multiple tools are valid, indicate the best choice and why.

    ---
    {format_instructions}
    ---
    Now, perform this evaluation based on the following inputs:

    **System Prompt:**
    {system_prompt}

    **User Question:**
    {user_question}

    **Context:**
    {context}
"""

TOOL_USAGE_PROMPT_TEMPLATE = """
    You are tasked with evaluating whether an AI agent correctly **used** a tool to respond to a user's question,, i.e. the right parameters were provided to the tool. You do **not** need to evaluate whether the correct tool was chosen — only whether the tool used was executed correctly.

    **Inputs:**
    - **System Prompt:** Instructions, constraints, and available tools for the AI agent.
    - **User Question:** The input provided by the user.
    - **Context:** The full chat history, including any prior tool calls and responses.

    ---
    ### **Your Task:**
    Analyze the provided information and evaluate whether the AI agent:

    **Tool Usage**
    - **0**: Tool Usage Incorrect (The tool was passed the wrong parameters or used incorrectly)
    - **1**: Tool Usage Correct (The tool was given the right parameters and was called correctly)
    - **2**: No Tool Selected/Tool Not Available (A tool was not available or the assistant did not use a tool)

    **IMPORTANT:**
    - Ignore whether the correct tool was chosen; only check if the tool was used properly (i.e., correct parameters were provided).
    - If the tool usage was incorrect, explain why (missing parameters, wrong format, etc.).
    - If the query is ambiguous, note if the AI should have asked for clarification.

    ---
    {format_instructions}

    ---
    Now, perform this evaluation based on the following inputs:

    **System Prompt:**
    {system_prompt}

    **User Question:**
    {user_question}

    **Context:**
    {context}
""" 