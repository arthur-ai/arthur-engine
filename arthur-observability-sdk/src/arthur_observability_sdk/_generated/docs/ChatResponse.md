# ChatResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**inference_id** | **str** | ID of the inference sent to the chat | 
**conversation_id** | **str** | ID of the conversation session | 
**timestamp** | **int** | Time the inference was made in unix milliseconds | 
**retrieved_context** | [**List[ChatDocumentContext]**](ChatDocumentContext.md) | related sections of documents that were most relevant to the inference prompt. Formatted as a list of retrieved context chunks which include document name, seq num, and context. | 
**llm_response** | **str** | response from the LLM for the original user prompt | 
**prompt_results** | [**List[ExternalRuleResult]**](ExternalRuleResult.md) | list of rule results for the user prompt | 
**response_results** | [**List[ExternalRuleResult]**](ExternalRuleResult.md) | list of rule results for the llm response | 
**model_name** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.chat_response import ChatResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ChatResponse from a JSON string
chat_response_instance = ChatResponse.from_json(json)
# print the JSON string representation of the object
print(ChatResponse.to_json())

# convert the object into a dict
chat_response_dict = chat_response_instance.to_dict()
# create an instance of ChatResponse from a dict
chat_response_from_dict = ChatResponse.from_dict(chat_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


