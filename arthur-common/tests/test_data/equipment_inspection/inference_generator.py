import base64
import random
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

# Use vanilla random for uuid seed
random.seed(42)
np.random.seed(42)

"""
Generate 1000 random inferences with the following columns:
- prompt_version_id (0-2)
- timestamp (7 day period)
- classification_gt (broken/functional/needs_repair_soon)
- classification_pred (same as gt, matches 70% of time)
- image (base64 encoded image)

Outputs:
inferences.csv - 1000 rows with all columns
"""

num_inferences = 1000
null_percentage = 0.04


def generate_simple_image():
    # Create a simple image with random shapes
    img = Image.new("RGB", (224, 224), color="white")
    draw = ImageDraw.Draw(img)

    # Draw some random shapes
    for _ in range(5):
        x1 = random.randint(0, 200)
        y1 = random.randint(0, 200)
        x2 = random.randint(x1, 224)
        y2 = random.randint(y1, 224)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.rectangle([x1, y1, x2, y2], fill=color)

    # Convert to base64 with data URI scheme
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


# Generate base data
prompt_version_ids = np.random.randint(0, 3, num_inferences)

start_date = datetime(2024, 1, 1)
timestamps = [
    start_date
    + timedelta(
        days=random.randint(0, 6),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    for _ in range(num_inferences)
]

classifications = ["broken", "functional", "needs_repair_soon"]
classification_gt = np.random.choice(classifications, num_inferences)

# Generate predictions that match ground truth 70% of the time
classification_pred = []
for gt in classification_gt:
    if random.random() < 0.7:
        classification_pred.append(gt)
    else:
        # Choose a different classification
        other_options = [c for c in classifications if c != gt]
        classification_pred.append(random.choice(other_options))

# Generate images
images = [generate_simple_image() for _ in range(num_inferences)]

# Create DataFrame
data = {
    "prompt_version_id": prompt_version_ids,
    "timestamp": timestamps,
    "classification_gt": classification_gt,
    "classification_pred": classification_pred,
    "image": images,
}

df = pd.DataFrame(data)

# Add null values only to classification_gt column
null_indices = np.random.choice(
    num_inferences,
    int(null_percentage * num_inferences),
    replace=False,
)
df.loc[null_indices, "classification_gt"] = np.nan

# Save all data to a single file
df.to_csv("inferences.csv", index=False)

# Display DataFrame
print("Inferences DataFrame (inferences.csv):")
print(df.head())
