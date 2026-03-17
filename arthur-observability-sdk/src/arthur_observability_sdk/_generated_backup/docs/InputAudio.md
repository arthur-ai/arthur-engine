# InputAudio


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | **str** | Base64 encoded audio data | 
**format** | **str** | audio format (e.g. &#39;mp3&#39;, &#39;wav&#39;, &#39;flac&#39;, etc.) | 

## Example

```python
from _generated.models.input_audio import InputAudio

# TODO update the JSON string below
json = "{}"
# create an instance of InputAudio from a JSON string
input_audio_instance = InputAudio.from_json(json)
# print the JSON string representation of the object
print(InputAudio.to_json())

# convert the object into a dict
input_audio_dict = input_audio_instance.to_dict()
# create an instance of InputAudio from a dict
input_audio_from_dict = InputAudio.from_dict(input_audio_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


