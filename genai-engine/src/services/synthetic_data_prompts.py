"""
Prompt templates for synthetic data generation.

This module contains the system and user prompt templates used
for generating synthetic dataset rows via LLM.
"""

from typing import Any, Dict, List

SYSTEM_PROMPT_TEMPLATE = """You are an expert at generating realistic, diverse synthetic data for datasets.
Your task is to generate or modify dataset rows based on the user's instructions.

Dataset Purpose:
{dataset_purpose}

Column Definitions:
{column_definitions}

Reference Examples (existing data from the dataset):
{reference_examples}

Guidelines:
1. Generate data that is realistic and consistent with the dataset purpose
2. Maintain diversity in the generated values
3. Follow the column descriptions carefully
4. Use the reference examples as a guide for the format and style of data
5. Each row should be unique and meaningful

IMPORTANT: You must respond with valid JSON containing:
- "rows": An array of row objects. Each row object has an "id" (string) and "data" (array of column objects with "column_name" and "column_value")
- "message": A brief explanation of what you did

Example response format:
{
    "rows": [
        {
            "id": "row_1",
            "data": [
                {"column_name": "col1", "column_value": "value1"},
                {"column_name": "col2", "column_value": "value2"}
            ]
        }
    ],
    "message": "Generated 5 new rows with diverse values..."
}"""


INITIAL_GENERATION_USER_PROMPT_TEMPLATE = """Generate {num_rows} new rows for this dataset.

Make sure each row is unique, realistic, and follows the column descriptions provided.
Assign each row a unique ID starting with "row_" followed by a number (e.g., "row_1", "row_2", etc.)."""


CONVERSATION_USER_PROMPT_TEMPLATE = """Current Generated Data:
{current_rows}

User Request:
{user_message}

Please update the data based on the user's request. You can:
- Add new rows (assign IDs like "row_N" where N continues from the highest existing number)
- Modify existing rows (keep their existing IDs)
- Remove rows that don't fit the request

Return the complete updated set of rows in your response."""


def format_column_definitions(
    column_descriptions: List[Dict[str, str]],
) -> str:
    """Format column descriptions into a readable string for the prompt."""
    lines = []
    for col in column_descriptions:
        lines.append(f"- {col['column_name']}: {col['description']}")
    return "\n".join(lines)


def format_reference_examples(
    existing_rows: List[Dict[str, str]],
    column_names: List[str],
    max_rows: int = 10,
) -> str:
    """Format existing dataset rows as reference examples."""
    if not existing_rows:
        return "(No existing data available)"

    # Limit to max_rows
    rows_to_show = existing_rows[:max_rows]

    lines = []
    for i, row in enumerate(rows_to_show, 1):
        row_parts = []
        for col in column_names:
            value = row.get(col, "")
            # Truncate long values
            if len(str(value)) > 100:
                value = str(value)[:100] + "..."
            row_parts.append(f"{col}={value}")
        lines.append(f"  Row {i}: {', '.join(row_parts)}")

    return "\n".join(lines)


def format_current_rows_for_prompt(
    current_rows: List[Dict[str, Any]],
    column_names: List[str],
) -> str:
    """Format the current generated rows for inclusion in conversation prompts."""
    if not current_rows:
        return "(No rows currently generated)"

    lines = []
    for row in current_rows:
        row_id = row.get("id", "unknown")
        data = row.get("data", [])
        row_values = []
        for col in column_names:
            # Find the value for this column
            value = ""
            for item in data:
                if item.get("column_name") == col:
                    value = item.get("column_value", "")
                    break
            # Truncate long values
            if len(str(value)) > 100:
                value = str(value)[:100] + "..."
            row_values.append(f"{col}={value}")
        lines.append(f"  [{row_id}]: {', '.join(row_values)}")

    return "\n".join(lines)


def build_system_prompt(
    dataset_purpose: str,
    column_descriptions: List[Dict[str, str]],
    existing_rows: List[Dict[str, str]],
    column_names: List[str],
) -> str:
    """Build the complete system prompt for synthetic data generation.

    User-controlled `dataset_purpose` is substituted LAST so that any
    literal placeholder strings inside it (e.g. ``{column_definitions}``)
    are not re-expanded by a subsequent `.replace()` call.
    """
    return (
        SYSTEM_PROMPT_TEMPLATE.replace(
            "{column_definitions}",
            format_column_definitions(column_descriptions),
        )
        .replace(
            "{reference_examples}",
            format_reference_examples(existing_rows, column_names),
        )
        .replace("{dataset_purpose}", dataset_purpose)
    )


def build_initial_generation_prompt(num_rows: int) -> str:
    """Build the user prompt for initial data generation."""
    return INITIAL_GENERATION_USER_PROMPT_TEMPLATE.format(num_rows=num_rows)


def build_conversation_prompt(
    user_message: str,
    current_rows: List[Dict[str, Any]],
    column_names: List[str],
) -> str:
    """Build the user prompt for conversation-based refinement."""
    return CONVERSATION_USER_PROMPT_TEMPLATE.format(
        current_rows=format_current_rows_for_prompt(current_rows, column_names),
        user_message=user_message,
    )
