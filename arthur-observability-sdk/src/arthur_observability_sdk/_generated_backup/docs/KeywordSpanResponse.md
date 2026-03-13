# KeywordSpanResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**keyword** | **str** | The keyword from the rule that matched within the input string. | 

## Example

```python
from _generated.models.keyword_span_response import KeywordSpanResponse

# TODO update the JSON string below
json = "{}"
# create an instance of KeywordSpanResponse from a JSON string
keyword_span_response_instance = KeywordSpanResponse.from_json(json)
# print the JSON string representation of the object
print(KeywordSpanResponse.to_json())

# convert the object into a dict
keyword_span_response_dict = keyword_span_response_instance.to_dict()
# create an instance of KeywordSpanResponse from a dict
keyword_span_response_from_dict = KeywordSpanResponse.from_dict(keyword_span_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


