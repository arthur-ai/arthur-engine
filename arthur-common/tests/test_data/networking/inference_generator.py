import random
import socket
import struct
from datetime import datetime, timedelta

import numpy as np

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# Function to generate random IP address
def generate_ip():
    return socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))


# Function to generate random datetime within a given range
def random_datetime(start, end) -> datetime:
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


# Function to generate uneven port distribution, mostly 443, 80 but some random ports
def uneven_port_distribution(num_points):
    ports = []
    ports.extend([443] * int(num_points * 0.5))
    ports.extend([80] * int(num_points * 0.3))
    ports.extend([random.randint(500, 2000) for _ in range(int(num_points * 0.2))])
    random.shuffle(ports)
    return ports


# Function to generate dataset
def generate_dataset(
    num_points,
    start_time: datetime,
    end_time: datetime,
) -> list[tuple]:
    # Pre-allocate arrays for better performance
    dataset = {
        "sent time": np.zeros(num_points, dtype="datetime64[ns]"),
        "received time": np.zeros(num_points, dtype="datetime64[ns]"),
        "packet origin": np.empty(num_points, dtype="U15"),
        "packet destination": np.empty(num_points, dtype="U15"),
        "packet size bytes": np.zeros(num_points, dtype=np.int32),
        "packet type": np.empty(num_points, dtype="U3"),
        "packet origin port": np.zeros(num_points, dtype=np.int32),
        "packet destination port": np.zeros(num_points, dtype=np.int32),
        "malicious": np.zeros(num_points, dtype=bool),
        "pred low accuracy malicious": np.zeros(num_points, dtype=bool),
        "pred high accuracy malicious": np.zeros(num_points, dtype=bool),
    }
    print("Arrays pre-allocated")

    # Generate timestamps with sinusoidal distribution
    delta = (end_time - start_time).total_seconds()
    # Create evenly spaced points across time range
    base_seconds = np.linspace(0, delta, num_points)
    # Add sinusoidal variation to create peaks and troughs in frequency
    variation = delta * 0.2 * np.sin(2 * np.pi * base_seconds / (delta / 4))
    time_seconds = base_seconds + variation
    # Clip to ensure we stay within time bounds
    time_seconds = np.clip(time_seconds, 0, delta)
    # Sort to maintain chronological order
    time_seconds.sort()
    dataset["sent time"] = np.array(
        [start_time + timedelta(seconds=s) for s in time_seconds],
        dtype="datetime64[ns]",
    )
    print("Sent timestamps generated")

    # Generate received times (1-100ms after sent_time)
    ms_delays = np.random.randint(1, 101, num_points)
    dataset["received time"] = dataset["sent time"] + ms_delays.astype(
        "timedelta64[ms]",
    )
    print("Received timestamps generated")

    # Generate IP addresses
    # Generate IPs with 5% nulls
    packet_origins = [
        generate_ip() if random.random() > 0.05 else None for _ in range(num_points)
    ]
    packet_destinations = [
        generate_ip() if random.random() > 0.05 else None for _ in range(num_points)
    ]
    dataset["packet origin"] = np.array(packet_origins)
    dataset["packet destination"] = np.array(packet_destinations)
    print("IP addresses generated with 5% nulls")

    # Generate packet sizes and types
    dataset["packet size bytes"] = np.random.randint(0, 101, num_points)
    # Create array with 90% TCP/UDP and 10% nulls
    packet_types = np.random.choice(
        ["TCP", "UDP", None],
        num_points,
        p=[0.45, 0.45, 0.1],
    )
    dataset["packet type"] = packet_types
    print("Packet sizes and types generated")

    # Generate ports using the uneven distribution
    ports = uneven_port_distribution(num_points)
    ports_arr = np.array(ports)
    dataset["packet origin port"] = np.random.choice(ports_arr, num_points)
    dataset["packet destination port"] = np.random.choice(ports_arr, num_points)
    print("Ports generated")

    # Calculate malicious flags vectorized
    dest_ports = dataset["packet destination port"]
    dataset["malicious"] = np.isin(dest_ports, list(range(700, 820)))
    dataset["pred low accuracy malicious"] = np.isin(dest_ports, [720, 800])
    dataset["pred high accuracy malicious"] = (dest_ports > 700) & (dest_ports < 900)
    print("Malicious flags calculated")

    return dataset


if __name__ == "__main__":
    # Define start and end time for the dataset
    start_time = datetime(2024, 11, 1, 0, 0, 0)
    end_time = datetime(2024, 12, 1, 0, 0, 0)

    # Generate dataset
    num_points = 25000
    dataset = generate_dataset(num_points, start_time, end_time)

    # Write dataset to a CSV file
    with open("network_packets_dataset.csv", "w") as file:
        # Write header
        file.write(
            "sent timestamp,received timestamp,packet origin,packet destination,packet size bytes,packet type,packet origin port,packet destination port,malicious,pred low accuracy malicious,pred high accuracy malicious\n",
        )

        # Zip all arrays together and write row by row
        for row in zip(
            dataset["sent time"],
            dataset["received time"],
            dataset["packet origin"],
            dataset["packet destination"],
            dataset["packet size bytes"],
            dataset["packet type"],
            dataset["packet origin port"],
            dataset["packet destination port"],
            dataset["malicious"],
            dataset["pred low accuracy malicious"],
            dataset["pred high accuracy malicious"],
        ):
            file.write(",".join(str(x) for x in row) + "\n")

    # Calculate confusion matrix metrics for low accuracy predictions
    true_pos_low = np.sum(
        (dataset["malicious"] == True)
        & (dataset["pred low accuracy malicious"] == True),
    )
    false_pos_low = np.sum(
        (dataset["malicious"] == False)
        & (dataset["pred low accuracy malicious"] == True),
    )
    true_neg_low = np.sum(
        (dataset["malicious"] == False)
        & (dataset["pred low accuracy malicious"] == False),
    )
    false_neg_low = np.sum(
        (dataset["malicious"] == True)
        & (dataset["pred low accuracy malicious"] == False),
    )

    # Calculate confusion matrix metrics for high accuracy predictions
    true_pos_high = np.sum(
        (dataset["malicious"] == True)
        & (dataset["pred high accuracy malicious"] == True),
    )
    false_pos_high = np.sum(
        (dataset["malicious"] == False)
        & (dataset["pred high accuracy malicious"] == True),
    )
    true_neg_high = np.sum(
        (dataset["malicious"] == False)
        & (dataset["pred high accuracy malicious"] == False),
    )
    false_neg_high = np.sum(
        (dataset["malicious"] == True)
        & (dataset["pred high accuracy malicious"] == False),
    )

    print("Dataset generated successfully!")

    print("\nRaw Counts:")
    print("\nGround Truth (malicious) Counts:")
    print(f"True: {np.sum(dataset['malicious'] == True)}")
    print(f"False: {np.sum(dataset['malicious'] == False)}")

    print("\nHigh Accuracy Predictor Counts:")
    print(f"True: {np.sum(dataset['pred high accuracy malicious'] == True)}")
    print(f"False: {np.sum(dataset['pred high accuracy malicious'] == False)}")

    print("\nLow Accuracy Predictor Counts:")
    print(f"True: {np.sum(dataset['pred low accuracy malicious'] == True)}")
    print(f"False: {np.sum(dataset['pred low accuracy malicious'] == False)}")

    print("\nLow Accuracy Predictor Metrics:")
    print(f"True Positives: {true_pos_low}")
    print(f"False Positives: {false_pos_low}")
    print(f"True Negatives: {true_neg_low}")
    print(f"False Negatives: {false_neg_low}")

    print("\nHigh Accuracy Predictor Metrics:")
    print(f"True Positives: {true_pos_high}")
    print(f"False Positives: {false_pos_high}")
    print(f"True Negatives: {true_neg_high}")
    print(f"False Negatives: {false_neg_high}")

"""
RANDOM_SEED = 42, n=25000 metrics:

Low Accuracy Predictor Metrics:
True Positives: 9
False Positives: 0
True Negatives: 24522
False Negatives: 469

High Accuracy Predictor Metrics:
True Positives: 477
False Positives: 266
True Negatives: 24256
False Negatives: 1
"""
