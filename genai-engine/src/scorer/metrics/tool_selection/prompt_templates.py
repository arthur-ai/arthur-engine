# Structured output prompt templates (without format_instructions)
TOOL_SELECTION_STRUCTURED_PROMPT_TEMPLATE = """
You are evaluating whether an AI agent selected the correct tool to answer a user's question.

Focus only on **tool selection**, not how the tool was used.

---

### **Evaluation Labels:**
- **0 = Incorrect** (Wrong tool(s) chosen)
- **1 = Correct** (Right tool(s) chosen)
- **2 = No Tool Used / Tool Not Available**

---

### **Key Principles:**
- **Chain-Aware**: A tool can be correct even if it doesn't answer the final question directly, as long as it's a necessary step.
- **History-Aware**: Tool choice should follow logically from earlier steps.
- **Strategic**: A valid step in a multi-step strategy is acceptable, even if not final.
- **Multiple Valid Tools**: If several are valid, any reasonable one is correct.
- **Tool Availability**: Don't penalize if a needed tool wasn't available.

---

### **Ignore:**
- Parameters passed to the tool.
- Whether the tool was executed correctly.

---

Now evaluate the following:

**System Prompt:**
{system_prompt}

**User Question:**
{user_query}

**Context:**
{context}
"""


TOOL_USAGE_STRUCTURED_PROMPT_TEMPLATE = """
You are evaluating whether a tool was **used correctly**, i.e., provided with the right parameters.

Focus only on **tool usage**, not tool selection.

---

### **Evaluation Labels:**
- **0 = Incorrect** (Wrong/missing parameters)
- **1 = Correct** (Right parameters given)
- **2 = No Tool Used / Tool Not Available**

---

### **Key Principles:**
- **Chain-Aware**: Parameters can be intermediate, they are not necessarily the final parameters.
- **Context-Aware**: Evaluate parameters based on information available so far.
- **Progressive Use**: Partial inputs are fine if they advance strategy.
---

### **Incorrect Usage If:**
- Wrong parameter format or values
- Key values clearly missing (and should have been requested)
- Tool used inconsistently with its purpose

---

Now evaluate the following:

**System Prompt:**
{system_prompt}

**User Question:**
{user_query}

**Context:**
{context}
"""


# Legacy prompt templates (with format_instructions)
TOOL_SELECTION_NON_STRUCTURED_PROMPT_TEMPLATE = (
    TOOL_SELECTION_STRUCTURED_PROMPT_TEMPLATE
    + """

    ---
    {format_instructions}
    ---"""
)

TOOL_USAGE_NON_STRUCTURED_PROMPT_TEMPLATE = (
    TOOL_USAGE_STRUCTURED_PROMPT_TEMPLATE
    + """

    ---
    {format_instructions}

    ---"""
)
