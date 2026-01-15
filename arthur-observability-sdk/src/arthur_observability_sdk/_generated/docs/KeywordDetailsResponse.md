# KeywordDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**keyword_matches** | [**List[KeywordSpanResponse]**](KeywordSpanResponse.md) | Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text. | [optional] [default to []]

## Example

```python
from arthur_observability_sdk._generated.models.keyword_details_response import KeywordDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of KeywordDetailsResponse from a JSON string
keyword_details_response_instance = KeywordDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(KeywordDetailsResponse.to_json())

# convert the object into a dict
keyword_details_response_dict = keyword_details_response_instance.to_dict()
# create an instance of KeywordDetailsResponse from a dict
keyword_details_response_from_dict = KeywordDetailsResponse.from_dict(keyword_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


