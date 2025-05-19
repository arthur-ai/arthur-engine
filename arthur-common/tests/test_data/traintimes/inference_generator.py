import random
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Major train stations for realistic data
STATIONS = [
    "Grand Central Terminal",
    "Penn Station",
    "Union Station",
    "South Station",
    "30th Street Station",
    "Chicago Union Station",
    "Los Angeles Union Station",
    "Portland Union Station",
    "Denver Union Station",
    "Dallas Union Station",
]


def generate_station_pairs(num_pairs: int) -> List[Tuple[str, str]]:
    """Generate unique pairs of departure and arrival stations"""
    pairs = []
    while len(pairs) < num_pairs:
        dep = random.choice(STATIONS)
        arr = random.choice(STATIONS)
        if dep != arr and (dep, arr) not in pairs:
            pairs.append((dep, arr))
    return pairs


def get_lateness_probability(date: datetime) -> float:
    """
    Calculate probability of lateness based on day of month
    Creates a sine wave with:
    - 30 day period
    - Range from 0.3 to 0.7 (30% to 70% chance of being late)
    """
    day = date.day
    # Convert day to radians (2π represents full period of 30 days)
    angle = (2 * np.pi * day) / 30
    # Generate sine wave between 0.3 and 0.7
    return 0.5 + 0.2 * np.sin(angle)


def get_prediction_accuracy(date: datetime) -> float:
    """
    Calculate prediction accuracy based on day of month
    Creates a sine wave with:
    - 21 day period (different from lateness period)
    - Range from 0.6 to 0.95 (60% to 95% accuracy)
    """
    day = date.day
    # Different period (21 days) creates interesting patterns
    angle = (2 * np.pi * day) / 21
    # Generate sine wave between 0.6 and 0.95
    return 0.775 + 0.175 * np.sin(angle)


def generate_datetime_range(
    start_date: str,
    end_date: str,
    num_points: int,
) -> List[datetime]:
    """Generate datetime objects with a bias towards rush hours"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    timestamps = []
    for _ in range(num_points):
        random_days = random.randint(0, (end - start).days)
        base_date = start + timedelta(days=random_days)

        # Rush hour bias
        if random.random() < 0.6:  # 60% chance of rush hour
            if random.random() < 0.5:
                # Morning rush with some variation
                hour = random.randint(6, 9)
            else:
                # Evening rush with some variation
                hour = random.randint(16, 19)
        else:
            # Non-rush hour
            hour = random.randint(0, 23)

        minute = random.randint(0, 59)
        timestamp = base_date.replace(hour=hour, minute=minute)
        timestamps.append(timestamp)

    return sorted(timestamps)


def generate_dataset(num_records: int, start_date: str, end_date: str) -> pd.DataFrame:
    """Generate the train delay prediction dataset"""

    # Generate departure timestamps
    departure_times = generate_datetime_range(start_date, end_date, num_records)

    # Generate station pairs
    station_pairs = [
        random.choice(generate_station_pairs(20)) for _ in range(num_records)
    ]
    departure_stations, arrival_stations = zip(*station_pairs)

    # Calculate scheduled journey times (2-8 hours with some variation)
    base_journey_times = np.random.uniform(2, 8, num_records)
    journey_variations = np.random.normal(0, 0.5, num_records)  # Add some noise
    journey_times = np.clip(base_journey_times + journey_variations, 1.5, 9)

    # Generate actual arrival times and lateness based on sinusoidal pattern
    arrival_times = []
    is_late = []

    for dep_time, journey_time in zip(departure_times, journey_times):
        scheduled_arrival = dep_time + timedelta(hours=journey_time)

        # Get lateness probability for this day
        late_prob = get_lateness_probability(dep_time)

        if random.random() < late_prob:
            # Generate delay with some randomness
            delay_minutes = random.randint(30, 180)  # 30min to 3hr delay
            actual_arrival = scheduled_arrival + timedelta(minutes=delay_minutes)
            is_late.append(True)
        else:
            # Add small random variation even when on time
            variation = timedelta(minutes=random.randint(-10, 15))
            actual_arrival = scheduled_arrival + variation
            is_late.append(False)
        arrival_times.append(actual_arrival)

    # Generate predictions based on sinusoidal accuracy pattern
    predictions = []
    for dep_time, late in zip(departure_times, is_late):
        accuracy = get_prediction_accuracy(dep_time)
        if random.random() < accuracy:
            predictions.append(late)  # Correct prediction
        else:
            predictions.append(not late)  # Incorrect prediction

    # Create DataFrame
    df = pd.DataFrame(
        {
            "departure_time": departure_times,
            "arrival_time": arrival_times,
            "departure_station": departure_stations,
            "arrival_station": arrival_stations,
            "is_late": is_late,
            "predicted_late": predictions,
        },
    )

    # Add platform numbers (5% null)
    df["departure_platform"] = [
        f"Platform {random.randint(1, 15)}" for _ in range(num_records)
    ]
    df.loc[df.sample(frac=0.05).index, "departure_platform"] = None

    # Add train numbers (10% null)
    df["train_number"] = [f"TR{random.randint(1000, 9999)}" for _ in range(num_records)]
    df.loc[df.sample(frac=0.10).index, "train_number"] = None

    # Add passenger count (15% null) - higher during rush hours
    passenger_counts = []
    for dt in departure_times:
        hour = dt.hour
        if 6 <= hour <= 9 or 16 <= hour <= 19:  # Rush hours
            count = random.randint(150, 300)
        else:
            count = random.randint(50, 200)
        passenger_counts.append(count)
    df["passenger_count"] = passenger_counts
    df.loc[df.sample(frac=0.15).index, "passenger_count"] = None

    return df


if __name__ == "__main__":
    # Generate dataset
    df = generate_dataset(
        num_records=50000,
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    # Save to CSV
    df.to_csv("train_delays.csv", index=False)

    # Print overall statistics
    late_percentage = (df["is_late"].sum() / len(df)) * 100
    correct_predictions = (df["is_late"] == df["predicted_late"]).sum()
    accuracy = (correct_predictions / len(df)) * 100

    print(f"\nOverall Dataset Statistics:")
    print(f"Total records: {len(df)}")
    print(f"Percentage of late trains: {late_percentage:.1f}%")
    print(f"Overall prediction accuracy: {accuracy:.1f}%")

    # Calculate confusion matrix
    true_positives = ((df["is_late"] == True) & (df["predicted_late"] == True)).sum()
    false_positives = ((df["is_late"] == False) & (df["predicted_late"] == True)).sum()
    true_negatives = ((df["is_late"] == False) & (df["predicted_late"] == False)).sum()
    false_negatives = ((df["is_late"] == True) & (df["predicted_late"] == False)).sum()

    print("\nConfusion Matrix:")
    print(f"True Positives: {true_positives}")
    print(f"False Positives: {false_positives}")
    print(f"True Negatives: {true_negatives}")
    print(f"False Negatives: {false_negatives}")

    # Print statistics by month
    print("\nMonthly Statistics:")
    df["month"] = df["departure_time"].dt.month
    monthly_stats = (
        df.groupby("month")
        .agg(
            {
                "is_late": ["count", "mean"],
                "predicted_late": "mean",
            },
        )
        .round(3)
    )

    # Calculate accuracy separately for each month
    monthly_accuracy = (
        df.groupby("month")
        .apply(lambda x: (x["is_late"] == x["predicted_late"]).mean())
        .round(3)
    )

    monthly_stats.columns = ["count", "late_rate", "predicted_late_rate"]
    monthly_stats["accuracy"] = monthly_accuracy

    print(monthly_stats)
