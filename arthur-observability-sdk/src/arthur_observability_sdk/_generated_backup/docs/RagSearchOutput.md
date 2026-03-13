# RagSearchOutput

Output from a RAG search execution

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**response** | [**RagProviderQueryResponse**](RagProviderQueryResponse.md) | RAG search response | 

## Example

```python
from _generated.models.rag_search_output import RagSearchOutput

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchOutput from a JSON string
rag_search_output_instance = RagSearchOutput.from_json(json)
# print the JSON string representation of the object
print(RagSearchOutput.to_json())

# convert the object into a dict
rag_search_output_dict = rag_search_output_instance.to_dict()
# create an instance of RagSearchOutput from a dict
rag_search_output_from_dict = RagSearchOutput.from_dict(rag_search_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


