# TokenUsageCount


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**inference** | **int** | Number of inference tokens sent to Arthur. | 
**eval_prompt** | **int** | Number of Prompt tokens incurred by Arthur rules. | 
**eval_completion** | **int** | Number of Completion tokens incurred by Arthur rules. | 
**user_input** | **int** | Number of user input tokens sent to Arthur. This field is deprecated and will be removed in the future. Use inference instead. | 
**prompt** | **int** | Number of Prompt tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_prompt instead. | 
**completion** | **int** | Number of Completion tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_completion instead. | 

## Example

```python
from _generated.models.token_usage_count import TokenUsageCount

# TODO update the JSON string below
json = "{}"
# create an instance of TokenUsageCount from a JSON string
token_usage_count_instance = TokenUsageCount.from_json(json)
# print the JSON string representation of the object
print(TokenUsageCount.to_json())

# convert the object into a dict
token_usage_count_dict = token_usage_count_instance.to_dict()
# create an instance of TokenUsageCount from a dict
token_usage_count_from_dict = TokenUsageCount.from_dict(token_usage_count_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


