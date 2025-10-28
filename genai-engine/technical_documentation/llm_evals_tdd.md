# Prompts LLM Evals Lifecycle Technical Design Doc

## Backend

### Modifications

- new enum to be added to the agentic_prompt class for whether the prompt is a “prompt” or an “llm_eval”. (< 1 day)
- change “/completions” to only allow running prompts of type “prompt” not llm_eval since those should run a saved prompt through the other completions route (< 1 day)
- change /tasks/{task_id}/prompts to only return prompts of type “prompt” (< 1 day)
- change /tasks/{task_id}/prompts/{prompt_id}/versions to only allow returning prompts of type “prompt” (< 1 day)
- change save endpoint to save prompts of only type ‘prompt’ (< 1 day)

### proposed new endpoints (1-2 days closer to 1 most likely)

- POST: /tasks/{task_id}/llm_evals
    - Creates a new version of a prompt which has the following parameters:
        - required:
            - name
            - model_provider
            - model_name
            - “evaluation_prompt” (the system prompt message)
            - score reasoning prompt - how the llm should explain its evaluation (will be in the response_format)
            - score range (also in the response_format, this will be static and binary to start we can expose this to the user in the future if we want)
            - Force type to be llm_eval (not exposted to user)
        - Optional:
            - The rest of the config settings (e.g. temperature) present in other prompts
- GET: /tasks/{task_id}/llm_evals
    - Lists all llm evals
    - force filter type to be llm_eval (not exposed to user)
- GET: /tasks/{task_id}/llm_evals/{evaluator_id}
    - Lists all versions of a specific llm_eval
    - Err if not type llm_eval

### Template llm evaluators

- First incorporate open-source evals provided by Ragas (~1-2 days, leaning towards 1 just depends how much effort it takes to include it)
- Creating our own custom llm-as-a-judge evals (the list below is straight from langfuse but we can change it)
    - Conciseness
    - Context correctness
    - context relevance
    - hallucination
    - helpfulness
    - relevance
    - toxicity
    - In terms of timing for each of these I could see each being 1 day, a few days or potentially even longer. Not sure how much time we want to dedicate to each of these. But finding datasets to benchmark each of these evaluators and iterating to find the best llm-as-a-judge prompt can definitely take some time.

### Questions

- Do we want to have a new separate llm_evals router or add these routes to the existing prompts router?
- I assume we want “GET: /tasks/{task_id}/prompts” to return only the prompts that will be of type ‘prompt’ after making the enum above. Do we want to have a separate get request to get all prompts and llm_evals?
- For getting a specific version, deleting all versions and deleting a specific version of an llm eval do we want to make new routes for it or use the existing prompt routes? because the functionality would be identical just under a different route name
- right now we have a unique constraint for prompt names, task_id and version. with the addition of prompt_type we could add it to the constraint. This would technically allow us to have duplicate names as long as they are different prompt types. Or, we could create an llm_evals table to keep them separate?