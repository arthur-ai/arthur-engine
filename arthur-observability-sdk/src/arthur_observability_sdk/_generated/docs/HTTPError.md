# HTTPError


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**detail** | **str** |  | 

## Example

```python
from arthur_observability_sdk._generated.models.http_error import HTTPError

# TODO update the JSON string below
json = "{}"
# create an instance of HTTPError from a JSON string
http_error_instance = HTTPError.from_json(json)
# print the JSON string representation of the object
print(HTTPError.to_json())

# convert the object into a dict
http_error_dict = http_error_instance.to_dict()
# create an instance of HTTPError from a dict
http_error_from_dict = HTTPError.from_dict(http_error_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


