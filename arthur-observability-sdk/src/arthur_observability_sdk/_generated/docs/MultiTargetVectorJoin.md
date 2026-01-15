# MultiTargetVectorJoin


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**combination** | [**MultiTargetVectorJoinEnum**](MultiTargetVectorJoinEnum.md) |  | 
**target_vectors** | **List[str]** |  | 
**weights** | [**Dict[str, MultiTargetVectorJoinWeightsValue]**](MultiTargetVectorJoinWeightsValue.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.multi_target_vector_join import MultiTargetVectorJoin

# TODO update the JSON string below
json = "{}"
# create an instance of MultiTargetVectorJoin from a JSON string
multi_target_vector_join_instance = MultiTargetVectorJoin.from_json(json)
# print the JSON string representation of the object
print(MultiTargetVectorJoin.to_json())

# convert the object into a dict
multi_target_vector_join_dict = multi_target_vector_join_instance.to_dict()
# create an instance of MultiTargetVectorJoin from a dict
multi_target_vector_join_from_dict = MultiTargetVectorJoin.from_dict(multi_target_vector_join_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


