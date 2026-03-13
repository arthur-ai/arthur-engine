# SearchDatasetsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of datasets matching the parameters. | 
**datasets** | [**List[DatasetResponse]**](DatasetResponse.md) | List of datasets matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from arthur_observability_sdk._generated.models.search_datasets_response import SearchDatasetsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SearchDatasetsResponse from a JSON string
search_datasets_response_instance = SearchDatasetsResponse.from_json(json)
# print the JSON string representation of the object
print(SearchDatasetsResponse.to_json())

# convert the object into a dict
search_datasets_response_dict = search_datasets_response_instance.to_dict()
# create an instance of SearchDatasetsResponse from a dict
search_datasets_response_from_dict = SearchDatasetsResponse.from_dict(search_datasets_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


