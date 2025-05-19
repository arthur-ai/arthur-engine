import json

"""
Chatgpt makes good test data, but struggles to make two datasets that have matching keys and can be joined
Use gpt to make emails.json, then this script to split it into inferences, ground truth, reference.

Prompt:
"write me a list of json objects. Each object should have three keys- content, label, id. Content should be the contents of an email written to a bank. The email should either be an innocent question, a complaint, or a praising comment comment.  The content of the email should populate the content key, and the label key should be one of question, complaint, comment. The id should be a uuid. "

*For variety, repeat a few times with subsequent prompts like:

"more but change the context to a golf ball company"

"""

emails = json.loads(open("emails.json", "r").read())

reference_proportion = 0.2
split = int(len(emails) // (1 / (1 - reference_proportion)))

reference_inferences = emails[split:]
emails = emails[:split]

ground_truth = [
    {"label": i["label"], "id": i["id"], "is_complaint": i["label"] == "complaint"}
    for i in emails
]
inferences = [{"content": i["content"], "id": i["id"]} for i in emails]

with open("ground_truth.json", "w") as f:
    json.dump(ground_truth, f)

with open("inferences.json", "w") as f:
    json.dump(inferences, f)

with open("reference_data.json", "w") as f:
    json.dump(reference_inferences, f)
