# HttpHeader

HTTP header with support for variable placeholders

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Header name (supports {{variable}} placeholders) | 
**value** | **str** | Header value (supports {{variable}} placeholders) | 

## Example

```python
from _generated.models.http_header import HttpHeader

# TODO update the JSON string below
json = "{}"
# create an instance of HttpHeader from a JSON string
http_header_instance = HttpHeader.from_json(json)
# print the JSON string representation of the object
print(HttpHeader.to_json())

# convert the object into a dict
http_header_dict = http_header_instance.to_dict()
# create an instance of HttpHeader from a dict
http_header_from_dict = HttpHeader.from_dict(http_header_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


