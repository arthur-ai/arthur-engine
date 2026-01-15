# QueryFeedbackResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**feedback** | [**List[InferenceFeedbackResponse]**](InferenceFeedbackResponse.md) | List of inferences matching the search filters. Length is less than or equal to page_size parameter | 
**page** | **int** | The current page number | 
**page_size** | **int** | The number of feedback items per page | 
**total_pages** | **int** | The total number of pages | 
**total_count** | **int** | The total number of feedback items matching the query parameters | 

## Example

```python
from _generated.models.query_feedback_response import QueryFeedbackResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QueryFeedbackResponse from a JSON string
query_feedback_response_instance = QueryFeedbackResponse.from_json(json)
# print the JSON string representation of the object
print(QueryFeedbackResponse.to_json())

# convert the object into a dict
query_feedback_response_dict = query_feedback_response_instance.to_dict()
# create an instance of QueryFeedbackResponse from a dict
query_feedback_response_from_dict = QueryFeedbackResponse.from_dict(query_feedback_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


