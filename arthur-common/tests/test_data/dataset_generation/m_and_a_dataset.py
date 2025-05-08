import random
import uuid
from datetime import datetime
from typing import Any, Dict

from sample_dataset import SampleDataset

# ONLY SUPPORTS BIGQUERY OUTPUT TODAY


class MAndADataset(SampleDataset):
    def __init__(self) -> None:
        self.model_uuid = str(uuid.uuid4())

    @property
    def inferences_per_file(self) -> int:
        return 10

    def file_name(self, date: datetime) -> str:
        date_str = date.strftime("%Y%m%d")
        return f"{self.model_uuid}/{date_str}/{str(uuid.uuid4())}.json"

    def generate_sample(self, timestamp: datetime) -> Dict[str, Any]:
        """generate sample dataset"""
        features = self._generate_AM_features()
        # generate prediction range based on date so prediction line doesn't flatten over time
        prediction_range_start, prediction_range_end = (
            self.generate_prediction_range_from_timestamp(timestamp)
        )
        features["inference_id"] = str(uuid.uuid4())
        features["timestamp"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        features["prediction"] = random.uniform(
            prediction_range_start,
            prediction_range_end,
        )
        if features["prediction"] > 0.95:
            # give the model a high chance of getting true positives
            features["ground_truth"] = random.choices([0, 1], weights=[0.05, 0.95])[0]
        else:
            # give the model a high change of getting true negatives
            features["ground_truth"] = random.choices([0, 1], weights=[0.95, 0.05])[0]
        return features

    @staticmethod
    def format_row_as_json(data: Dict[str, Any]) -> Dict[str, Any]:
        return data

    @staticmethod
    def _generate_AM_features() -> Dict[str, Any]:
        return {
            "Revenue": random.randint(0, 10000000),
            "Net Income": random.randint(0, 10000000),
            "Profit Margin": random.randint(0, 1000),
            "Earnings Per Share": random.uniform(1, 10),
            "Debt Equity Ratio": random.uniform(0, 1),
            "Market Capitalization": random.randint(0, 100000000000),
            "Cash Reserves": random.randint(0, 10000000),
            "Liquidity Ratio": random.uniform(0, 1),
            "Revenue Growth Rate": random.choices(
                [random.uniform(0, 100), None],
                weights=[0.75, 0.25],
            )[0],
            "Enterprise Value": random.randint(0, 1000000000),
            "Market Share": random.uniform(0, 100),
            "Industry Growth Rate": random.choices(
                [random.uniform(0, 100), None],
                weights=[0.75, 0.25],
            )[0],
            "Number of Competitors": random.randint(0, 100),
            "Geographical Reach": random.choice(["global", "regional", None]),
            "Brand Value": random.randint(0, 1000000),
            "Geographic Overlap": random.choice(["significant", "insignificant", None]),
            "Complementary Products Services": random.choice([True, False]),
            "Customer Base Overlap": random.choice(["small", "medium", "large"]),
            "Strategic Alignment": {
                "Overlap in Products Services": random.randint(0, 10),
                "Supply Chain Dependencies": random.randint(0, 30),
                "Technology IP Assets": random.randint(0, 15),
                "Market Expansion Potential": random.randint(0, 80),
            },
            "MA History": {
                "Past Acquisition Activity": random.randint(0, 10),
                "Collaboration History": random.randint(0, 300),
                "Regulatory Hurdles": random.randint(0, 10),
            },
        }
