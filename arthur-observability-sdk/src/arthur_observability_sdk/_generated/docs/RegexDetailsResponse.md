# RegexDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**regex_matches** | [**List[RegexSpanResponse]**](RegexSpanResponse.md) | Each string in this list corresponds to a matching span from the input text that matches the configured regex rule. | [optional] [default to []]

## Example

```python
from arthur_observability_sdk._generated.models.regex_details_response import RegexDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RegexDetailsResponse from a JSON string
regex_details_response_instance = RegexDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(RegexDetailsResponse.to_json())

# convert the object into a dict
regex_details_response_dict = regex_details_response_instance.to_dict()
# create an instance of RegexDetailsResponse from a dict
regex_details_response_from_dict = RegexDetailsResponse.from_dict(regex_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


