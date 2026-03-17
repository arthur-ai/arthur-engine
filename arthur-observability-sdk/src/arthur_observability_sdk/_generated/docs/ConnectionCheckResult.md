# ConnectionCheckResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**connection_check_outcome** | [**ConnectionCheckOutcome**](ConnectionCheckOutcome.md) | Result of the connection check. | 
**failure_reason** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.connection_check_result import ConnectionCheckResult

# TODO update the JSON string below
json = "{}"
# create an instance of ConnectionCheckResult from a JSON string
connection_check_result_instance = ConnectionCheckResult.from_json(json)
# print the JSON string representation of the object
print(ConnectionCheckResult.to_json())

# convert the object into a dict
connection_check_result_dict = connection_check_result_instance.to_dict()
# create an instance of ConnectionCheckResult from a dict
connection_check_result_from_dict = ConnectionCheckResult.from_dict(connection_check_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


