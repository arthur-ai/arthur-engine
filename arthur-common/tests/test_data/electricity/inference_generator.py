from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

STAR_WARS_CITIES = [
    "Coruscant",
    "Theed",
    "Mos Eisley",
    "Cloud City",
    "Keren",
    "Iziz",
    "Coronet",
    "Tipoca City",
    "Pau City",
    "Canto Bight",
]


def generate_duck_curve(num_points, noise_level=0.1, hours=None):
    """Generate a duck curve based on hours of day."""
    if hours is None:
        hours = np.linspace(0, 24, num_points)

    # Base load
    base_load = 40 + np.zeros(num_points)

    # Morning ramp
    morning_ramp = 20 * np.exp(-((hours - 6) ** 2) / 2)

    # Evening peak
    evening_peak = 30 * np.exp(-((hours - 19) ** 2) / 4)

    # Combine components
    curve = base_load + morning_ramp + evening_peak

    # Add noise
    noise = np.random.normal(0, noise_level * np.mean(curve), num_points)
    curve = curve + noise

    return np.clip(curve, 0, None)


def generate_solar_curve(num_points, noise_level=0.05, hours=None):
    """Generate a solar generation curve based on hours of day."""
    if hours is None:
        hours = np.linspace(0, 24, num_points)

    # Solar generation (bell curve centered at noon)
    solar = 50 * np.exp(-((hours - 12) ** 2) / 8)

    # Add noise
    noise = np.random.normal(0, noise_level * np.mean(solar), num_points)
    solar = solar + noise

    return np.clip(solar, 0, None)


def generate_dataset(start_time: datetime, end_time: datetime, points_per_minute=1):
    """
    Generate energy dataset for arbitrary time range.

    Args:
        start_time: Start datetime
        end_time: End datetime
        points_per_minute: Number of data points per minute (default 10)
    """
    # Calculate total minutes and points
    total_minutes = int((end_time - start_time).total_seconds() / 60)
    num_points = total_minutes * points_per_minute

    # Generate timestamps
    timestamps = [
        start_time + timedelta(minutes=i / points_per_minute) for i in range(num_points)
    ]

    # Convert timestamps to hour of day (0-24) for pattern generation
    hours_of_day = np.array(
        [(t.hour + t.minute / 60 + t.second / 3600) for t in timestamps],
    )

    # Generate base curves for each city
    city_data = []

    for city in STAR_WARS_CITIES:
        # Generate consumption curves using hour of day
        base_consumption = generate_duck_curve(
            num_points,
            noise_level=0.1,
            hours=hours_of_day,
        )
        actual_consumption = base_consumption * (
            1 + np.random.normal(0, 0.05, num_points)
        )

        # Generate solar first
        solar = generate_solar_curve(num_points, hours=hours_of_day)

        # Calculate remaining demand after solar
        remaining_demand = actual_consumption - solar

        # Split remaining demand between nuclear and hypermatter
        nuclear_base = 0.6 * remaining_demand
        hypermatter_base = 0.4 * remaining_demand

        # Add small variations to make it realistic
        nuclear = nuclear_base + np.random.normal(0, 1, num_points)
        hypermatter = hypermatter_base + np.random.normal(0, 1.5, num_points)

        # Ensure no negative generation
        nuclear = np.clip(nuclear, 0, None)
        hypermatter = np.clip(hypermatter, 0, None)

        # Total generation is sum of components
        total_generation = solar + nuclear + hypermatter

        # Expected values have small variations from actual
        expected_generation = total_generation * (
            1 + np.random.normal(0, 0.03, num_points)
        )

        # Create mask for 5% nulls (different for each column)
        null_masks = {
            "city": np.random.choice([True, False], num_points, p=[0.05, 0.95]),
            "energy usage consumption": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "expected energy consumption": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "energy generation": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "expected energy generation": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "solar generation": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "nuclear generation": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
            "hypermatter generation": np.random.choice(
                [True, False],
                num_points,
                p=[0.05, 0.95],
            ),
        }

        # Create city-specific dataframe with nulls
        city_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "city": np.where(null_masks["city"], None, city),
                "energy usage consumption": np.where(
                    null_masks["energy usage consumption"],
                    None,
                    actual_consumption,
                ),
                "expected energy consumption": np.where(
                    null_masks["expected energy consumption"],
                    None,
                    base_consumption,
                ),
                "energy generation": np.where(
                    null_masks["energy generation"],
                    None,
                    total_generation,
                ),
                "expected energy generation": np.where(
                    null_masks["expected energy generation"],
                    None,
                    expected_generation,
                ),
                "solar generation": np.where(
                    null_masks["solar generation"],
                    None,
                    solar,
                ),
                "nuclear generation": np.where(
                    null_masks["nuclear generation"],
                    None,
                    nuclear,
                ),
                "hypermatter generation": np.where(
                    null_masks["hypermatter generation"],
                    None,
                    hypermatter,
                ),
            },
        )

        city_data.append(city_df)

    # Combine all cities
    dataset = pd.concat(city_data, ignore_index=True)
    return dataset


def create_visualizations(dataset):
    # Convert timestamp to hour of day for better visualization
    dataset["hour"] = (
        pd.to_datetime(dataset["timestamp"]).dt.hour
        + pd.to_datetime(dataset["timestamp"]).dt.minute / 60
    )

    # Create a large figure with subplots for each city
    fig, axes = plt.subplots(5, 2, figsize=(20, 40))
    fig.suptitle("Energy Metrics by City", fontsize=16, y=0.92)

    # Flatten axes for easier iteration
    axes_flat = axes.flatten()

    for idx, city in enumerate(STAR_WARS_CITIES):
        ax = axes_flat[idx]
        city_data = dataset[dataset["city"] == city].copy()

        # Plot consumption lines
        ax.plot(
            city_data["hour"],
            city_data["energy usage consumption"],
            label="Actual Consumption",
            color="blue",
        )
        ax.plot(
            city_data["hour"],
            city_data["expected energy consumption"],
            label="Expected Consumption",
            color="blue",
            linestyle="--",
        )

        # Fill nulls with 0 for stackplot (temporary for visualization only)
        solar_plot = city_data["solar generation"].fillna(0)
        nuclear_plot = city_data["nuclear generation"].fillna(0)
        hypermatter_plot = city_data["hypermatter generation"].fillna(0)

        # Plot stacked generation
        ax.fill_between(
            city_data["hour"],
            0,
            solar_plot,
            label="Solar",
            color="yellow",
            alpha=0.5,
        )
        ax.fill_between(
            city_data["hour"],
            solar_plot,
            solar_plot + nuclear_plot,
            label="Nuclear",
            color="green",
            alpha=0.5,
        )
        ax.fill_between(
            city_data["hour"],
            solar_plot + nuclear_plot,
            solar_plot + nuclear_plot + hypermatter_plot,
            label="Hypermatter",
            color="purple",
            alpha=0.5,
        )

        # Plot expected generation line
        ax.plot(
            city_data["hour"],
            city_data["expected energy generation"],
            label="Expected Generation",
            color="red",
            linestyle="--",
        )

        # Customize plot
        ax.set_title(f"{city}")
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Energy")
        ax.set_xlim(0, 24)
        ax.grid(True, alpha=0.3)

        # Add legend to first plot only
        if idx == 0:
            ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Adjust layout
    plt.tight_layout()

    # Save figure
    plt.savefig("energy_charts_all_cities.png", dpi=300, bbox_inches="tight")
    print("Generated chart for all cities")
    plt.close()


if __name__ == "__main__":
    start_time = datetime(2024, 11, 17, 0, 0, 0)
    end_time = datetime(2024, 11, 17, 23, 59, 59)

    dataset = generate_dataset(start_time, end_time)

    # Save to CSV
    dataset.to_csv("energy_dataset.csv", index=False)

    # Generate visualizations
    try:
        print("\nGenerating visualizations...")
        create_visualizations(dataset)
        print("Visualization complete! Check energy_charts_all_cities.png")
    except ImportError:
        print(
            "\nMatplotlib not installed. To generate visualizations, install matplotlib with:",
        )
        print("pip install matplotlib")

    # Print dataset-wide statistics
    print("\nDataset Statistics:")
    print(f"Total rows: {len(dataset)}")
    print(f"Unique cities: {dataset['city'].nunique()}")
    print(f"Time range: {dataset['timestamp'].min()} to {dataset['timestamp'].max()}")

    # Verify generation components sum to total
    generation_sum = (
        dataset["solar generation"]
        + dataset["nuclear generation"]
        + dataset["hypermatter generation"]
    )
    generation_diff = np.abs(generation_sum - dataset["energy generation"])
    print(
        f"\nMax difference between sum of components and total generation: {generation_diff.max():.6f}",
    )

    # Calculate dataset-wide MAE
    consumption_mae = np.mean(
        np.abs(
            dataset["energy usage consumption"]
            - dataset["expected energy consumption"],
        ),
    )
    generation_mae = np.mean(
        np.abs(dataset["energy generation"] - dataset["expected energy generation"]),
    )

    print(f"\nOverall Dataset MAE:")
    print(f"Consumption MAE: {consumption_mae:.2f}")
    print(f"Generation MAE: {generation_mae:.2f}")

    # Calculate per-city MAE
    print("\nPer-City MAE:")
    for city in STAR_WARS_CITIES:
        city_data = dataset[dataset["city"] == city]

        city_consumption_mae = np.mean(
            np.abs(
                city_data["energy usage consumption"]
                - city_data["expected energy consumption"],
            ),
        )
        city_generation_mae = np.mean(
            np.abs(
                city_data["energy generation"]
                - city_data["expected energy generation"],
            ),
        )

        print(f"\n{city}:")
        print(f"  Consumption MAE: {city_consumption_mae:.2f}")
        print(f"  Generation MAE: {city_generation_mae:.2f}")

    # Calculate per-city MSE
    print("\nPer-City MSE:")
    for city in STAR_WARS_CITIES:
        city_data = dataset[dataset["city"] == city]

        city_consumption_mse = np.mean(
            np.pow(
                city_data["energy usage consumption"]
                - city_data["expected energy consumption"],
                2,
            ),
        )
        city_generation_mse = np.mean(
            np.pow(
                city_data["energy generation"]
                - city_data["expected energy generation"],
                2,
            ),
        )

        print(f"\n{city}:")
        print(f"  Consumption MSE: {city_consumption_mse:.2f}")
        print(f"  Generation MSE: {city_generation_mse:.2f}")

    # Print null percentages
    print("\nNull Percentages:")
    for column in dataset.columns:
        null_pct = (dataset[column].isnull().sum() / len(dataset)) * 100
        print(f"{column}: {null_pct:.1f}%")
