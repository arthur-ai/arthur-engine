# QueryInferencesResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of inferences matching the query parameters | 
**inferences** | [**List[ExternalInference]**](ExternalInference.md) | List of inferences matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from arthur_observability_sdk._generated.models.query_inferences_response import QueryInferencesResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QueryInferencesResponse from a JSON string
query_inferences_response_instance = QueryInferencesResponse.from_json(json)
# print the JSON string representation of the object
print(QueryInferencesResponse.to_json())

# convert the object into a dict
query_inferences_response_dict = query_inferences_response_instance.to_dict()
# create an instance of QueryInferencesResponse from a dict
query_inferences_response_from_dict = QueryInferencesResponse.from_dict(query_inferences_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


