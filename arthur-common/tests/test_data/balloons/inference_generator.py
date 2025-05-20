import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Use vanilla random for uuid seed
random.seed(42)
np.random.seed(42)
"""
Generate 1000 random flights. All columns except passenger_count (int) / night_flight (bool) will have exactly 4% null / nan / None values.

Prediction column - crashed is whether or not the flight crashed. Hardcoded to be some arbitrary condition based on the features

Outputs:
flights.csv - 850 rows
reference.csv - 150 rows
ground_truth.csv - 1000 rows
"""

num_flights = 1000
null_percentage = 0.04

flight_ids = [
    uuid.UUID(int=random.getrandbits(128), version=4) for _ in range(num_flights)
]

max_altitudes = np.random.uniform(1000, 5000, num_flights)
max_altitudes[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan
max_altitudes = np.around(max_altitudes, decimals=5)

distances = np.random.uniform(50, 500, num_flights)
distances[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan
distances = np.around(distances, decimals=5)

flight_starts = [
    datetime(
        2024,
        np.random.randint(1, 13),
        np.random.randint(1, 29),
        np.random.randint(0, 24),
        np.random.randint(0, 60),
        np.random.randint(0, 60),
    )
    for _ in range(num_flights)
]

flight_ends = [
    start + timedelta(hours=np.random.randint(1, 6)) for start in flight_starts
]

flight_starts = np.array(flight_starts)
flight_ends = np.array(flight_ends)

flight_starts[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan
flight_ends[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan

customer_feedback = ["Positive", "Neutral", "Negative", "Highly Negative"]
feedback_col = customer_feedback * (num_flights // len(customer_feedback))
feedback_col = np.array(feedback_col)
feedback_col[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan

weather_conditions = ["Sunny", "Cloudy", "Rainy", "Windy"]
weather_col = weather_conditions * (num_flights // len(weather_conditions))
weather_col = np.array(weather_col)
weather_col[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan


night_flight = [True, False]
night_col = night_flight * (num_flights // len(night_flight))
np.random.shuffle(night_col)

passenger_counts = np.random.randint(1, 10, num_flights)

max_speeds = np.random.uniform(10, 50, num_flights)
max_speeds[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan
max_speeds = np.around(max_speeds, decimals=5)

loaded_fuels = np.random.uniform(50, 200, num_flights)
loaded_fuels[
    np.random.choice(num_flights, int(null_percentage * num_flights), replace=False)
] = np.nan
loaded_fuels = np.around(loaded_fuels, decimals=5)

data = {
    "flight id": flight_ids,
    "max altitude": max_altitudes,
    "distance": distances,
    "flight start": flight_starts,
    "flight end": flight_ends,
    "customer feedback": feedback_col,
    "weather conditions": weather_col,
    "night flight": night_col,
    "passenger count": passenger_counts,
    "max speed": max_speeds,
    "loaded fuel": loaded_fuels,
}

df = pd.DataFrame(data)

# Add 'crashed' column
df["crashed"] = (
    (df["weather conditions"] != "Sunny")
    & (df["passenger count"] > 5)
    & (df["max altitude"] > 1000)
)

# Save the first 85% of rows without the 'crashed' column
n = int(num_flights * 0.85)
flights_df = df.head(n).drop(columns=["crashed"])
flights_df.to_csv("flights.csv", index=False)

# Save flight_id and crashed columns for top n rows
ground_truth_df = df.head(n)[["flight id", "crashed"]]
ground_truth_df.to_csv("ground_truth.csv", index=False)

# Save the remaining rows with the 'crashed' column for reference data
flights_reference_df = df.tail(num_flights - n)
flights_reference_df.to_csv("reference.csv", index=False)

# Display DataFrames
print("Flights DataFrame (flights.csv):")
print(flights_df.head())
print("\nReference DataFrame (reference.csv):")
print(flights_reference_df.head())
print("\nGround Truth DataFrame (ground_truth.csv):")
print(ground_truth_df.head())
