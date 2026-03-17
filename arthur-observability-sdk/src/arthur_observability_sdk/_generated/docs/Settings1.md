# Settings1

Settings configuration for a search request to a RAG provider. None if version has been soft-deleted.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**collection_name** | **str** | Name of the vector collection used for the search. | 
**limit** | **int** |  | [optional] 
**include_vector** | [**IncludeVector**](IncludeVector.md) |  | [optional] 
**offset** | **int** |  | [optional] 
**auto_limit** | **int** |  | [optional] 
**return_metadata** | [**ReturnMetadata**](ReturnMetadata.md) |  | [optional] 
**return_properties** | **List[str]** |  | [optional] 
**rag_provider** | **str** |  | [optional] [default to 'weaviate']
**search_kind** | **str** |  | [optional] [default to 'keyword_search']
**alpha** | **float** | Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search. | [optional] [default to 0.7]
**query_properties** | **List[str]** |  | [optional] 
**fusion_type** | [**HybridFusion**](HybridFusion.md) |  | [optional] 
**max_vector_distance** | **float** |  | [optional] 
**minimum_match_or_operator** | **int** |  | [optional] 
**and_operator** | **bool** |  | [optional] 
**target_vector** | [**TargetVector1**](TargetVector1.md) |  | [optional] 
**certainty** | **float** |  | [optional] 
**distance** | **float** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.settings1 import Settings1

# TODO update the JSON string below
json = "{}"
# create an instance of Settings1 from a JSON string
settings1_instance = Settings1.from_json(json)
# print the JSON string representation of the object
print(Settings1.to_json())

# convert the object into a dict
settings1_dict = settings1_instance.to_dict()
# create an instance of Settings1 from a dict
settings1_from_dict = Settings1.from_dict(settings1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


