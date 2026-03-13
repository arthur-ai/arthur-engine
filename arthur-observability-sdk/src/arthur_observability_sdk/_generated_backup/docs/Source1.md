# Source1

Source of the variable value

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;dataset_column&#39; | 
**dataset_column** | [**DatasetColumnSource**](DatasetColumnSource.md) | Dataset column source | 
**experiment_output** | [**ExperimentOutputSource**](ExperimentOutputSource.md) | Experiment output source | 

## Example

```python
from _generated.models.source1 import Source1

# TODO update the JSON string below
json = "{}"
# create an instance of Source1 from a JSON string
source1_instance = Source1.from_json(json)
# print the JSON string representation of the object
print(Source1.to_json())

# convert the object into a dict
source1_dict = source1_instance.to_dict()
# create an instance of Source1 from a dict
source1_from_dict = Source1.from_dict(source1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


