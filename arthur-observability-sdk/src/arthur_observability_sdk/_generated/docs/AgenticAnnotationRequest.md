# AgenticAnnotationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**annotation_score** | **int** | Binary score for whether a traces has been liked or disliked (0 &#x3D; disliked, 1 &#x3D; liked) | 
**annotation_description** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_annotation_request import AgenticAnnotationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticAnnotationRequest from a JSON string
agentic_annotation_request_instance = AgenticAnnotationRequest.from_json(json)
# print the JSON string representation of the object
print(AgenticAnnotationRequest.to_json())

# convert the object into a dict
agentic_annotation_request_dict = agentic_annotation_request_instance.to_dict()
# create an instance of AgenticAnnotationRequest from a dict
agentic_annotation_request_from_dict = AgenticAnnotationRequest.from_dict(agentic_annotation_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


