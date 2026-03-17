# ListAgenticAnnotationsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**annotations** | [**List[AgenticAnnotationResponse]**](AgenticAnnotationResponse.md) | List of annotations | 
**count** | **int** | Total number of annotations | 

## Example

```python
from arthur_observability_sdk._generated.models.list_agentic_annotations_response import ListAgenticAnnotationsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListAgenticAnnotationsResponse from a JSON string
list_agentic_annotations_response_instance = ListAgenticAnnotationsResponse.from_json(json)
# print the JSON string representation of the object
print(ListAgenticAnnotationsResponse.to_json())

# convert the object into a dict
list_agentic_annotations_response_dict = list_agentic_annotations_response_instance.to_dict()
# create an instance of ListAgenticAnnotationsResponse from a dict
list_agentic_annotations_response_from_dict = ListAgenticAnnotationsResponse.from_dict(list_agentic_annotations_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


