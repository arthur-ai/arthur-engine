# TargetVector1

Specifies vector to use for similarity search when using named vectors.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**combination** | [**MultiTargetVectorJoinEnum**](MultiTargetVectorJoinEnum.md) |  | 
**target_vectors** | **List[str]** |  | 
**weights** | [**Dict[str, MultiTargetVectorJoinWeightsValue]**](MultiTargetVectorJoinWeightsValue.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.target_vector1 import TargetVector1

# TODO update the JSON string below
json = "{}"
# create an instance of TargetVector1 from a JSON string
target_vector1_instance = TargetVector1.from_json(json)
# print the JSON string representation of the object
print(TargetVector1.to_json())

# convert the object into a dict
target_vector1_dict = target_vector1_instance.to_dict()
# create an instance of TargetVector1 from a dict
target_vector1_from_dict = TargetVector1.from_dict(target_vector1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


