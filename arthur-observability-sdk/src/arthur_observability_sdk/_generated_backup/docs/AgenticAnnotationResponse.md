# AgenticAnnotationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the annotation | 
**annotation_type** | [**AgenticAnnotationType**](AgenticAnnotationType.md) | Type of annotation | 
**trace_id** | **str** | ID of the trace this annotation belongs to | 
**continuous_eval_id** | **str** |  | [optional] 
**continuous_eval_name** | **str** |  | [optional] 
**eval_name** | **str** |  | [optional] 
**eval_version** | **int** |  | [optional] 
**annotation_score** | **int** |  | [optional] 
**annotation_description** | **str** |  | [optional] 
**input_variables** | [**List[VariableTemplateValue]**](VariableTemplateValue.md) |  | [optional] 
**run_status** | [**ContinuousEvalRunStatus**](ContinuousEvalRunStatus.md) |  | [optional] 
**cost** | **float** |  | [optional] 
**created_at** | **datetime** | Time the annotation was created | 
**updated_at** | **datetime** | Time the annotation was last updated | 

## Example

```python
from _generated.models.agentic_annotation_response import AgenticAnnotationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticAnnotationResponse from a JSON string
agentic_annotation_response_instance = AgenticAnnotationResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticAnnotationResponse.to_json())

# convert the object into a dict
agentic_annotation_response_dict = agentic_annotation_response_instance.to_dict()
# create an instance of AgenticAnnotationResponse from a dict
agentic_annotation_response_from_dict = AgenticAnnotationResponse.from_dict(agentic_annotation_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


