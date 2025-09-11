from scorer.checks.hallucination.v2_legacy_prompts import get_flagging_prompt


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
            "context": "A couple common data drift metrics are: Kullback-Leibler Divergence (KL Divergence) and Kolmogorov-Smirnov (KS) Test",
            "num_texts": "1",
            "text_list_str": "- Kullback-Leibler Divergence (KL Divergence)\n- Kolmogorov-Smirnov (KS) Test\n- Precision / Recall / F1 Score",
            "output": """[
                LLMClaimResult(claim_text="Kullback-Leibler Divergence (KL Divergence)", is_hallucination=False, explanation="This is a common data drift metric."),
                LLMClaimResult(claim_text="Kolmogorov-Smirnov (KS) Test", is_hallucination=False, explanation="This is also a common data drift metric."),
                LLMClaimResult(claim_text="Precision / Recall / F1 Score", is_hallucination=True, explanation="These metrics were not mentioned in the context.")
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
            "context": "Generate a sentence with line breaks.",
            "num_texts": "1",
            "text_list_str": "- This is a line break that should be on two separate lines.",
            "output": """[
                LLMClaimResult(
                    claim_text="This is a line break that should be on two separate lines.",
                    is_hallucination=True,
                    explanation="The claim is unsupported because this text does not contain any line breaks"
                )
            ]""",
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
            ]""",
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
