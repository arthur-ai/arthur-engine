# TransformExtractionResponseList


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | [**List[VariableTemplateValue]**](VariableTemplateValue.md) | List of extracted variables. | 

## Example

```python
from arthur_observability_sdk._generated.models.transform_extraction_response_list import TransformExtractionResponseList

# TODO update the JSON string below
json = "{}"
# create an instance of TransformExtractionResponseList from a JSON string
transform_extraction_response_list_instance = TransformExtractionResponseList.from_json(json)
# print the JSON string representation of the object
print(TransformExtractionResponseList.to_json())

# convert the object into a dict
transform_extraction_response_list_dict = transform_extraction_response_list_instance.to_dict()
# create an instance of TransformExtractionResponseList from a dict
transform_extraction_response_list_from_dict = TransformExtractionResponseList.from_dict(transform_extraction_response_list_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


