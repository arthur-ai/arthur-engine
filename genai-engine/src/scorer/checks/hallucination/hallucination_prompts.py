from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
)

def get_flagging_prompt(flagging_examples, flagging_instruction, end_instruction):
    flagging_example_template = PromptTemplate.from_template(
        "\n=\nContext: {context}\n{num_texts} Texts\n{text_list_str}\n{num_texts} Labels: ",
    )

    flagging_prompt_template_messages = [
        SystemMessagePromptTemplate.from_template(flagging_instruction)
    ]

    for example in flagging_examples:
        formatted_example = flagging_example_template.format(
            context=example["context"],
            num_texts=example["num_texts"],
            text_list_str=example["text_list_str"],
        )
        human_message = HumanMessagePromptTemplate.from_template(formatted_example)
        ai_message = AIMessagePromptTemplate.from_template(example["output"])
        flagging_prompt_template_messages.extend([human_message, ai_message])

    flagging_prompt_template_messages.append(
        HumanMessagePromptTemplate.from_template(end_instruction)
    )

    flag_text_batch_template = ChatPromptTemplate.from_messages(
        flagging_prompt_template_messages,
    )

    return flag_text_batch_template
    

def get_structured_output_prompt(): 
    flagging_examples = [
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there are dogs eating my shoes\n- it hurts",
            "output": """[
                LLMClaimResult(claim_text="there are dogs eating my shoes", is_hallucination=False, explanation="The claim is directly supported by the context."),
                LLMClaimResult(claim_text="it hurts", is_hallucination=False, explanation="The claim is directly supported by the context.")
            ]""",
        },
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there are dogs eating my shoes\n- it does not hurt",
            "output": """[
                LLMClaimResult(claim_text="there are dogs eating my shoes", is_hallucination=False, explanation="The context confirms that dogs are eating the shoes."),
                LLMClaimResult(claim_text="it does not hurt", is_hallucination=True, explanation="The claim contradicts the context, which states that it hurts.")
            ]""",
        },
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there is no pain\n - there are two animals",
            "output": """[
                LLMClaimResult(claim_text="there is no pain", is_hallucination=True, explanation="The claim contradicts the context, which states that it hurts."),
                LLMClaimResult(claim_text="there are two animals", is_hallucination=False, explanation="The context mentions two dogs, which supports this claim.")
            ]""",
        },
        {
            "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
            "num_texts": "3",
            "text_list_str": "- the actor is terrible\n- the actor didnt deserve an award\n- the actor is terrible because they have released no movies",
            "output": """[
                LLMClaimResult(claim_text="the actor is terrible", is_hallucination=False, explanation="The context states the performer is terrible."),
                LLMClaimResult(claim_text="the actor didnt deserve an award", is_hallucination=False, explanation="The word 'inexplicably' implies the award was undeserved."),
                LLMClaimResult(claim_text="the actor is terrible because they have released no movies", is_hallucination=True, explanation="The context says they released a movie, contradicting the claim.")
            ]""",
        },
        {
            "context": "What are common data drift metrics?",
            "num_texts": "1",
            "text_list_str": "- Kullback-Leibler Divergence (KL Divergence)\n- Kolmogorov-Smirnov (KS) Test\n- Precision / Recall / F1 Score",
            "output": """[
                LLMClaimResult(claim_text="Kullback-Leibler Divergence (KL Divergence)", is_hallucination=False, explanation="This is a common data drift metric."),
                LLMClaimResult(claim_text="Kolmogorov-Smirnov (KS) Test", is_hallucination=False, explanation="This is also a common data drift metric."),
                LLMClaimResult(claim_text="Precision / Recall / F1 Score", is_hallucination=True, explanation="These are not common data drift metrics.")
            ]""",
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "num_texts": "4",
            "text_list_str": "- BERT came out in 2019\n- BERT is an NLP model\n- LLMs are also NLP models\n- ChatGPT is a great new NLP model",
            "output": """[
                LLMClaimResult(claim_text="BERT came out in 2019", is_hallucination=False, explanation="The context references BERT as the most advanced model as of 2019."),
                LLMClaimResult(claim_text="BERT is an NLP model", is_hallucination=False, explanation="The context directly states this."),
                LLMClaimResult(claim_text="LLMs are also NLP models", is_hallucination=True, explanation="LLMs are not mentioned in the context."),
                LLMClaimResult(claim_text="ChatGPT is a great new NLP model", is_hallucination=True, explanation="ChatGPT is not referenced in the context.")
            ]""",
        },
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "1",
            "text_list_str": "- it does not hurt",
            "output": """[
                LLMClaimResult(
                    claim_text="it does not hurt",
                    is_hallucination=True,
                    explanation="The claim is unsupported because the context mentions that it hurts, but the claim mentions it does not, which is a contradiction."
                )
            ]"""
        },
        {
            "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
            "num_texts": "1",
            "text_list_str": "- the actor is terrible because they have released no movies",
            "output": """[
                LLMClaimResult(
                    claim_text="the actor is terrible because they have released no movies",
                    is_hallucination=True,
                    explanation="The claim is unsupported because the context mentions that the actor is bad, but not because of a lack of movies."
                )
            ]"""
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "num_texts": "1",
            "text_list_str": "- ChatGPT is a great new LLM.",
            "output": """[
                LLMClaimResult(
                    claim_text="ChatGPT is a great new LLM.",
                    is_hallucination=True,
                    explanation="The claim is unsupported because ChatGPT is not mentioned in the context."
                )
            ]"""
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "num_texts": "1",
            "text_list_str": "- BERT is a solid model.",
            "output": """[
                LLMClaimResult(
                    claim_text="BERT is a solid model.",
                    is_hallucination=False,
                    explanation="The claim is supported because it references BERT, the advanced NLP model mentioned in the context."
                )
            ]"""
        },
        {
            "context": "Generate a sentence with line breaks.",
            "num_texts": "1",
            "text_list_str": "- This is a line break that should be on two separate lines.",
            "output": """[
                LLMClaimResult(
                    claim_text="This is a line break that should be on two separate lines.",
                    is_hallucination=True,
                    explanation="The claim is unsupported because this text does not contain any line breaks"
                )
            ]"""
        },
        {
            "context": "Generate a sentence with line breaks.",
            "num_texts": "1",
            "text_list_str": "- This is a line break\nthat should be on two separate lines.",
            "output": """[
                LLMClaimResult(
                    claim_text="This is a line break that should be on two separate lines.",
                    is_hallucination=False,
                    explanation="The claim is supported because the text contains a line break"
                )
            ]"""
        },
    ]

    flagging_instruction = """
    You are evaluating whether each claim is supported by the given context. 
    For each claim, return a structured object in this format:

    LLMClaimResult(claim_text=(str), is_hallucination=(bool), explanation=(str))

    - claim_text is the original text of the claim
    - is_hallucination is a boolean that indicates if the claim is supported by the context
    - explanation is the reason why the claim is supported or not supported by the context

    ** Important **

    For Claim Validation (LLMClaimResult.is_hallucination):
    - If a claim is directly supported by the context, set is_hallucination=False.
    - If the context does not mention or contradicts the claim, set is_hallucination=True.
    - Only consider the context when deciding — ignore outside knowledge.
    - It does not matter if a text was true according to your training data, the only information that matters was the context.
    - Claims about people, places, events, software needed to occur in the context for you to allow it in a text.
    - If something is mentioned in the text that is not in the context, you label is_hallucination=True.

    For Claim Explanation (LLMClaimResult.explanation):
    - The reader needs to be able to understand in a lot of detail which parts of the claims were OK,
    which parts of the claims lacked evidence within the context and why the evidence was lacking.
    - You only offer explanations and did not offer additional assistance other than the explanation.

    Your output must be a Python list of LLMClaimResult(...) entries, one for each input claim.
    Do not return any extra text — just the list.

    =Examples=
    """

    end_instruction = "=Now the real thing=\nMake sure that you include only {num_texts} LLMClaimResults or else you will fail.\nContext: {context}\n{num_texts} Texts\n{text_list_str}\n{num_texts} Labels: "

    return get_flagging_prompt(flagging_examples, flagging_instruction, end_instruction)

def get_claim_flagging_prompt():
    flagging_examples = [
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there are dogs eating my shoes\n- it hurts",
            "output": "0,0",
        },
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there are dogs eating my shoes\n- it does not hurt",
            "output": "0,1",
        },
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "num_texts": "2",
            "text_list_str": "- there is no pain\n - there are two animals",
            "output": "1,0",
        },
        {
            "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
            "num_texts": "3",
            "text_list_str": "- the actor is terrible\n- the actor didnt deserve an award\n- the actor is terrible because they have released no movies",
            "output": "0,0,1",
        },
        {
            "context": "What are common data drift metrics?",
            "num_texts": "1",
            "text_list_str": "- Kullback-Leibler Divergence (KL Divergence)\n- Kolmogorov-Smirnov (KS) Test\n- Precision / Recall / F1 Score",
            "output": "0,0,1",
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "num_texts": "4",
            "text_list_str": "- BERT came out in 2019\n- BERT is an NLP model\n- LLMs are also NLP models\n- ChatGPT is a great new NLP model",
            "output": "0,0,1,1",
        },
    ]

    flagging_instruction = """
    You took a batch of texts and flagged the ones that lacked supporting evidence in the context.
    If a text was valid, you labeled it a 0. If a text did not have any supporting evidence in the context, you labeled it a 1.

    It did not matter if a text was true according to your training data - the only information that mattered was the context.
    Claims about people, places, events, software needed to occur in the context for you to have allowed it in a text.
    If something is mentioned in the text that is not in the context, you label it a 1.
    You did not do anything else other than labeling.
    =Examples=
    """

    end_instruction = "=Now the real thing=\nMake sure that you include only {num_texts} labels or else you will fail.\nContext: {context}\n{num_texts} Texts\n{text_list_str}\n{num_texts} Labels: "

    return get_flagging_prompt(flagging_examples, flagging_instruction, end_instruction)

def get_flagged_claim_explanation_prompt():
    explanation_examples = [
        {
            "context": "There are two dogs eating my shoes and it hurts",
            "flagged_claim": "it does not hurt",
            "output": "the claim is unsupported because the context mentions that it hurts, but the claim mentions it does not, which is a contradiction",
        },
        {
            "context": "After the terrible performer released an awful movie, they inexplicably won an Oscar.",
            "flagged_claim": "the actor is terrible because they have released no movies",
            "output": "the claim is unsupported because the context mentions that the actor is bad, but not because of a lack of movies",
        },
        {
            "context": "What are common data drift metrics?",
            "flagged_claim": "Precision / Recall / F1 Score",
            "output": "the claim is unsupported because these are not common data drift metrics",
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "flagged_claim": "ChatGPT is a great new LLM.",
            "output": "the claim is unsupported because ChatGPT is not mentioned in the context",
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "flagged_claim": "BERT is a solid model.",
            "output": "the claim is supported because it references BERT the advanced NLP model",
        },
        {
            "context": "This software library is only usable in the context of NLP, and the most advanced NLP model to date so far (2019) is BERT from Google.",
            "flagged_claim": "Hello!",
            "output": "the claim is supported because this is just dialog",
        },
    ]

    explanation_instruction = """
    You explained why claims were flagged as unsupported by the contexts they were evaluated against.
    The reader needed to be able to understand in a lot of detail which parts of the claims were OK,
    and which parts of the claims lacked evidence within the context, and why the evidence was lacking.
    You only offer explanations and did not offer additional assistance other than the explanation.

    That is why you generated useful explanations like this:
    =Examples=
    """

    explanation_example_template = PromptTemplate.from_template(
        "\n=\nContext: {context}\nFlagged Claim: {claim}\nExplanation: ",
    )

    explanation_prompt_template_messages = [
        SystemMessagePromptTemplate.from_template(explanation_instruction)
    ]

    for example in explanation_examples:
        formatted_explanation_example_template = explanation_example_template.format(
            context=example["context"],
            claim=example["flagged_claim"],
        )
        human_message = HumanMessagePromptTemplate.from_template(
            formatted_explanation_example_template,
        )
        ai_message = AIMessagePromptTemplate.from_template(example["output"])
        explanation_prompt_template_messages.extend([human_message, ai_message])

    explanation_prompt_template_messages.append(
        HumanMessagePromptTemplate.from_template(
            "Now the real thing\n=\nContext: {context}\nFlagged Claim: {claim}\nExplanation: ",
        ),
    )

    explanation_template = ChatPromptTemplate.from_messages(
        explanation_prompt_template_messages,
    )

    return explanation_template