# Source2

Source of the variable value

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;dataset_column&#39; | 
**dataset_column** | [**DatasetColumnSource**](DatasetColumnSource.md) | Dataset column source | 
**generator_type** | **str** | Type of generator to use. Currently supports &#39;uuid&#39; for UUID generation. | 

## Example

```python
from _generated.models.source2 import Source2

# TODO update the JSON string below
json = "{}"
# create an instance of Source2 from a JSON string
source2_instance = Source2.from_json(json)
# print the JSON string representation of the object
print(Source2.to_json())

# convert the object into a dict
source2_dict = source2_instance.to_dict()
# create an instance of Source2 from a dict
source2_from_dict = Source2.from_dict(source2_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


