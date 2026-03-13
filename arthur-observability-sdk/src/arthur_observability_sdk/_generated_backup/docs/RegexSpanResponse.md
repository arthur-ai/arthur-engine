# RegexSpanResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**matching_text** | **str** | The subtext within the input string that matched the regex rule. | 
**pattern** | **str** |  | [optional] 

## Example

```python
from _generated.models.regex_span_response import RegexSpanResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RegexSpanResponse from a JSON string
regex_span_response_instance = RegexSpanResponse.from_json(json)
# print the JSON string representation of the object
print(RegexSpanResponse.to_json())

# convert the object into a dict
regex_span_response_dict = regex_span_response_instance.to_dict()
# create an instance of RegexSpanResponse from a dict
regex_span_response_from_dict = RegexSpanResponse.from_dict(regex_span_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


