# IncludeVector

Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from arthur_observability_sdk._generated.models.include_vector import IncludeVector

# TODO update the JSON string below
json = "{}"
# create an instance of IncludeVector from a JSON string
include_vector_instance = IncludeVector.from_json(json)
# print the JSON string representation of the object
print(IncludeVector.to_json())

# convert the object into a dict
include_vector_dict = include_vector_instance.to_dict()
# create an instance of IncludeVector from a dict
include_vector_from_dict = IncludeVector.from_dict(include_vector_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


