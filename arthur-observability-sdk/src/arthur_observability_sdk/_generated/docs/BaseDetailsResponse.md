# BaseDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.base_details_response import BaseDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BaseDetailsResponse from a JSON string
base_details_response_instance = BaseDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(BaseDetailsResponse.to_json())

# convert the object into a dict
base_details_response_dict = base_details_response_instance.to_dict()
# create an instance of BaseDetailsResponse from a dict
base_details_response_from_dict = BaseDetailsResponse.from_dict(base_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


