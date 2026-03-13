# FileUploadResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**name** | **str** |  | 
**type** | **str** |  | 
**word_count** | **int** |  | 
**success** | **bool** |  | 

## Example

```python
from arthur_observability_sdk._generated.models.file_upload_result import FileUploadResult

# TODO update the JSON string below
json = "{}"
# create an instance of FileUploadResult from a JSON string
file_upload_result_instance = FileUploadResult.from_json(json)
# print the JSON string representation of the object
print(FileUploadResult.to_json())

# convert the object into a dict
file_upload_result_dict = file_upload_result_instance.to_dict()
# create an instance of FileUploadResult from a dict
file_upload_result_from_dict = FileUploadResult.from_dict(file_upload_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


