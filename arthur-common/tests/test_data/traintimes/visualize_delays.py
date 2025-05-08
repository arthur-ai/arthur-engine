import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Read the data
df = pd.read_csv("train_delays.csv")

# Convert timestamps to datetime
df["departure_time"] = pd.to_datetime(df["departure_time"])

# Create daily counts
daily_stats = (
    df.groupby(df["departure_time"].dt.date)
    .agg({"is_late": ["count", "sum"], "predicted_late": "sum"})
    .reset_index()
)

# Flatten column names
daily_stats.columns = ["date", "total_trains", "actual_late", "predicted_late"]

# Convert date to datetime for better x-axis formatting
daily_stats["date"] = pd.to_datetime(daily_stats["date"])

# Create the visualization
plt.figure(figsize=(15, 8))
sns.set_style("whitegrid")

# Plot both lines
plt.plot(
    daily_stats["date"],
    daily_stats["actual_late"],
    label="Actually Late",
    color="red",
    alpha=0.7,
)
plt.plot(
    daily_stats["date"],
    daily_stats["predicted_late"],
    label="Predicted Late",
    color="blue",
    alpha=0.7,
)

# Customize the plot
plt.title("Train Delays: Actual vs Predicted (Daily)", fontsize=14, pad=20)
plt.xlabel("Date", fontsize=12)
plt.ylabel("Number of Trains", fontsize=12)
plt.legend(fontsize=10)

# Rotate x-axis labels for better readability
plt.xticks(rotation=45)

# Adjust layout to prevent label cutoff
plt.tight_layout()

# Save the plot
plt.savefig("train_delays_visualization.png")
plt.close()

# Print some summary statistics
print("\nSummary Statistics (Daily):")
print(f"Average number of trains per day: {daily_stats['total_trains'].mean():.1f}")
print(f"Average number of late trains per day: {daily_stats['actual_late'].mean():.1f}")
print(
    f"Average number of predicted late trains per day: {daily_stats['predicted_late'].mean():.1f}",
)
