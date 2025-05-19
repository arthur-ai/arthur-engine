import csv
import random
from datetime import datetime, timedelta

import numpy as np

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Define the classes
vehicle_types = ["Car", "Truck", "Motorcycle"]


# Function to generate a synthetic sample
def generate_vehicle_sample(base_time, index):
    # Simulated sensor data
    speed = round(random.gauss(70, 15), 1)  # in mph
    weight = round(random.gauss(3000, 1200), 1)  # in pounds
    engine_temp = round(random.gauss(190, 20), 1)  # in Fahrenheit
    tire_pressure = round(random.gauss(32, 5), 1)  # in PSI

    # Timestamp: simulate each row as 10 seconds apart
    timestamp = (base_time + timedelta(seconds=index * 10)).isoformat() + "Z"

    # True label based on simple rules
    if weight > 5000:
        true_label = "Truck"
    elif weight < 1000:
        true_label = "Motorcycle"
    else:
        true_label = "Car"

    # Add some noise to simulate prediction errors
    if random.random() < 0.85:  # 85% chance the prediction is correct
        predicted_label = true_label
    else:
        predicted_label = random.choice([v for v in vehicle_types if v != true_label])

    return {
        "Timestamp": timestamp,
        "Speed": speed,
        "Weight": weight,
        "EngineTemp": engine_temp,
        "TirePressure": tire_pressure,
        "PredictedLabel": predicted_label,
        "TrueLabel": true_label,
    }


# Generate CSV
def generate_csv(filename="vehicle_classification_data.csv", num_rows=200):
    base_time = datetime.utcnow()
    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Timestamp",
                "Speed",
                "Weight",
                "EngineTemp",
                "TirePressure ",
                "PredictedLabel",
                "TrueLabel",
            ],
        )
        writer.writeheader()
        for i in range(num_rows):
            writer.writerow(generate_vehicle_sample(base_time, i))

    print(f"Sample dataset with timestamps saved to '{filename}'.")


# Run it
if __name__ == "__main__":
    generate_csv()
