# TargetVector

Specifies vector to use for vector search when using named vectors.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**combination** | [**MultiTargetVectorJoinEnum**](MultiTargetVectorJoinEnum.md) |  | 
**target_vectors** | **List[str]** |  | 
**weights** | [**Dict[str, MultiTargetVectorJoinWeightsValue]**](MultiTargetVectorJoinWeightsValue.md) |  | [optional] 

## Example

```python
from _generated.models.target_vector import TargetVector

# TODO update the JSON string below
json = "{}"
# create an instance of TargetVector from a JSON string
target_vector_instance = TargetVector.from_json(json)
# print the JSON string representation of the object
print(TargetVector.to_json())

# convert the object into a dict
target_vector_dict = target_vector_instance.to_dict()
# create an instance of TargetVector from a dict
target_vector_from_dict = TargetVector.from_dict(target_vector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


