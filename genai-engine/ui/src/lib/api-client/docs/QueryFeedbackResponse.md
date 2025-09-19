# QueryFeedbackResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**feedback** | [**Array&lt;InferenceFeedbackResponse&gt;**](InferenceFeedbackResponse.md) | List of inferences matching the search filters. Length is less than or equal to page_size parameter | [default to undefined]
**page** | **number** | The current page number | [default to undefined]
**page_size** | **number** | The number of feedback items per page | [default to undefined]
**total_pages** | **number** | The total number of pages | [default to undefined]
**total_count** | **number** | The total number of feedback items matching the query parameters | [default to undefined]

## Example

```typescript
import { QueryFeedbackResponse } from './api';

const instance: QueryFeedbackResponse = {
    feedback,
    page,
    page_size,
    total_pages,
    total_count,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
